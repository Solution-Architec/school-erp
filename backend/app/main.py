import os
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, or_
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, get_db, SessionLocal
from . import models, schemas
from .security import hash_password, verify_password, create_access_token, current_user, require_roles

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for table in ("users", "students", "staff", "classes", "vehicles", "hostels", "documents", "maintenance_requests", "fee_structures", "student_fees", "fee_payments"):
            conn.execute(text('ALTER TABLE "' + table + '" ADD COLUMN IF NOT EXISTS school_id INTEGER REFERENCES schools(id)'))
        for table in ("students", "staff", "classes", "vehicles", "hostels", "documents", "maintenance_requests", "fee_structures", "student_fees", "fee_payments"):
            conn.execute(text('ALTER TABLE "' + table + '" ALTER COLUMN school_id SET NOT NULL'))

        for index_name in ("ix_students_admission_no", "ix_staff_employee_no", "ix_vehicles_registration_no", "ix_fee_payments_receipt_no"):
            conn.execute(text('DROP INDEX IF EXISTS "' + index_name + '"'))
        conn.execute(text("ALTER TABLE fee_structures DROP CONSTRAINT IF EXISTS uq_fee_structure_name_year_term"))
        conn.execute(text("ALTER TABLE fee_structures DROP CONSTRAINT IF EXISTS uq_fee_structure_school_year_term"))
        conn.execute(text("ALTER TABLE fee_structures ADD CONSTRAINT uq_fee_structure_school_year_term UNIQUE (school_id, name, academic_year, term)"))
        conn.execute(text("ALTER TABLE fee_payments DROP CONSTRAINT IF EXISTS uq_fee_payment_school_receipt"))
        conn.execute(text("ALTER TABLE fee_payments ADD CONSTRAINT uq_fee_payment_school_receipt UNIQUE (school_id, receipt_no)"))
        for table, constraint, columns in (
            ("students", "uq_student_school_admission", "school_id, admission_no"),
            ("staff", "uq_staff_school_employee", "school_id, employee_no"),
            ("vehicles", "uq_vehicle_school_registration", "school_id, registration_no"),
        ):
            conn.execute(text('ALTER TABLE "' + table + '" DROP CONSTRAINT IF EXISTS "' + constraint + '"'))
            conn.execute(text('ALTER TABLE "' + table + '" ADD CONSTRAINT "' + constraint + '" UNIQUE (' + columns + ')'))

    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe123!")
    with SessionLocal() as db:
        if not db.scalar(select(models.User).where(models.User.email == email)):
            db.add(models.User(name=os.getenv("BOOTSTRAP_ADMIN_NAME", "ERP Administrator"),
                               email=email, password_hash=hash_password(password), role="super_admin"))
            db.commit()
    yield

app = FastAPI(title="School ERP API", version="0.1.0",
              description="Starter ERP API. Review security and complete domain workflows before production.",
              lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "school-erp-api"}

@app.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == form.username))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer",
            "user": schemas.UserOut.model_validate(user).model_dump()}

@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user

def school_scope(model, user):
    if user.role == "super_admin":
        return None
    if not user.school_id:
        raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
    return model.school_id == user.school_id


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    def count(model, *conditions):
        stmt = select(func.count()).select_from(model)
        scope = school_scope(model, user)
        if scope is not None:
            stmt = stmt.where(scope)
        if conditions:
            stmt = stmt.where(*conditions)
        return db.scalar(stmt) or 0
    return {
        "students": count(models.Student),
        "staff": count(models.Staff),
        "classes": count(models.SchoolClass),
        "vehicles": count(models.Vehicle),
        "hostel_rooms": count(models.Hostel),
        "open_maintenance": count(models.MaintenanceRequest, models.MaintenanceRequest.status == "open"),
        "user_role": user.role
    }


def register_crud(path, model, schema_in, schema_out, roles):
    def validate_related_records(values, user, db):
        if model is models.StudentFee:
            student = db.get(models.Student, values.get("student_id"))
            if not student or (user.role != "super_admin" and student.school_id != user.school_id):
                raise HTTPException(status_code=404, detail="Student not found in your school")
            structure_id = values.get("fee_structure_id")
            if structure_id:
                structure = db.get(models.FeeStructure, structure_id)
                if not structure or (user.role != "super_admin" and structure.school_id != user.school_id):
                    raise HTTPException(status_code=404, detail="Fee structure not found in your school")
        if model is models.Document and values.get("owner_type") == "student":
            student = db.get(models.Student, values.get("owner_id"))
            if not student or (user.role != "super_admin" and student.school_id != user.school_id):
                raise HTTPException(status_code=404, detail="Document owner not found in your school")
    def list_items(q: str = Query(default="", max_length=120), limit: int = Query(default=100, ge=1, le=500),
                   offset: int = Query(default=0, ge=0), db: Session = Depends(get_db),
                   user: models.User = Depends(require_roles(*roles))):
        stmt = select(model)
        scope = school_scope(model, user)
        if scope is not None:
            stmt = stmt.where(scope)
        if q and model is models.Student:
            term = f"%{q}%"
            stmt = stmt.where(or_(
                models.Student.full_name.ilike(term),
                models.Student.admission_no.ilike(term),
                models.Student.guardian_phone.ilike(term),
            ))
        elif q and hasattr(model, "full_name"):
            stmt = stmt.where(model.full_name.ilike(f"%{q}%"))
        elif q and hasattr(model, "name"):
            stmt = stmt.where(model.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(model.id.desc()).offset(offset).limit(limit)
        return list(db.scalars(stmt).all())

    def create_item(payload: Any, db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles(*roles))):
        values = payload.model_dump()
        validate_related_records(values, user, db)
        if hasattr(model, "school_id"):
            if user.role != "super_admin":
                values["school_id"] = user.school_id
            elif not values.get("school_id"):
                raise HTTPException(status_code=422, detail="school_id is required for Super Admin record creation")
        if model is models.Document:
            values["uploaded_by"] = user.id
        obj = model(**values)
        db.add(obj)
        try:
            db.commit()
            db.refresh(obj)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Duplicate or invalid record")
        return obj

    def get_item(item_id: int, db: Session = Depends(get_db),
                 user: models.User = Depends(require_roles(*roles))):
        obj = db.get(model, item_id)
        if not obj or (user.role != "super_admin" and obj.school_id != user.school_id):
            raise HTTPException(status_code=404, detail="Record not found")
        return obj

    def update_item(item_id: int, payload: Any, db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles(*roles))):
        obj = db.get(model, item_id)
        if not obj or (user.role != "super_admin" and obj.school_id != user.school_id):
            raise HTTPException(status_code=404, detail="Record not found")
        values = payload.model_dump()
        validate_related_records(values, user, db)
        for key, value in values.items():
            setattr(obj, key, value)
        try:
            db.commit()
            db.refresh(obj)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Duplicate or invalid record")
        return obj

    def delete_item(item_id: int, db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles("super_admin", "admin"))):
        obj = db.get(model, item_id)
        if not obj or (user.role != "super_admin" and obj.school_id != user.school_id):
            raise HTTPException(status_code=404, detail="Record not found")
        db.delete(obj)
        db.commit()
        return {"deleted": True}

    list_items.__name__ = f"list_{path.replace('-', '_')}"
    create_item.__name__ = f"create_{path.replace('-', '_')}"
    get_item.__name__ = f"get_{path.replace('-', '_')}"
    update_item.__name__ = f"update_{path.replace('-', '_')}"
    delete_item.__name__ = f"delete_{path.replace('-', '_')}"
    create_item.__annotations__["payload"] = schema_in
    update_item.__annotations__["payload"] = schema_in
    app.add_api_route(f"/api/{path}", list_items, methods=["GET"], response_model=list[schema_out], tags=[path])
    app.add_api_route(f"/api/{path}", create_item, methods=["POST"], response_model=schema_out, tags=[path])
    app.add_api_route(f"/api/{path}/{{item_id}}", get_item, methods=["GET"], response_model=schema_out, tags=[path])
    app.add_api_route(f"/api/{path}/{{item_id}}", update_item, methods=["PUT"], response_model=schema_out, tags=[path])
    app.add_api_route(f"/api/{path}/{{item_id}}", delete_item, methods=["DELETE"], tags=[path])


ADMIN_ROLES = ("super_admin", "admin")
FINANCE_ROLES = ("super_admin", "admin", "accountant")
@app.post("/api/students/import", tags=["students"])
async def import_students(file: UploadFile = File(...), db: Session = Depends(get_db),
                         user: models.User = Depends(require_roles("admin"))):
    if not user.school_id:
        raise HTTPException(status_code=403, detail="Assign this admin account to a school before importing students")
    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="Upload a .csv or .xlsx file")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")
    try:
        if filename.endswith(".csv"):
            import csv, io
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            records = list(reader)
        else:
            from openpyxl import load_workbook
            import io
            workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            sheet = workbook.active
            values = sheet.iter_rows(values_only=True)
            headers = [str(v).strip() if v is not None else "" for v in next(values, ())]
            records = [dict(zip(headers, row)) for row in values if any(v is not None for v in row)]
            workbook.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")
    if not records:
        raise HTTPException(status_code=400, detail="The file has no student rows")
    if len(records) > 5000:
        raise HTTPException(status_code=400, detail="Maximum 5,000 students per upload")
    allowed = set(schemas.StudentIn.model_fields.keys())
    existing_stmt = select(models.Student.admission_no)
    if user.role != "super_admin":
        existing_stmt = existing_stmt.where(models.Student.school_id == user.school_id)
    existing = set(db.scalars(existing_stmt).all())
    seen, accepted, errors = set(), [], []
    skipped = 0
    for row_number, source in enumerate(records, start=2):
        row = {str(k).strip().lower(): v for k, v in source.items() if k is not None}
        data = {k: v for k, v in row.items() if k in allowed and v is not None}
        admission = str(data.get("admission_no", "")).strip()
        if not admission:
            errors.append({"row": row_number, "error": "Admission number is required"})
            skipped += 1
            continue
        if admission in existing or admission in seen:
            errors.append({"row": row_number, "error": f"Duplicate admission number: {admission}"})
            skipped += 1
            continue
        for key in ("transport_required", "hostel_required"):
            if key in data and isinstance(data[key], str):
                data[key] = data[key].strip().lower() in ("1", "true", "yes", "y")
        if "date_of_birth" in data and hasattr(data["date_of_birth"], "isoformat"):
            value = data["date_of_birth"]
            data["date_of_birth"] = value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
        try:
            student = schemas.StudentIn.model_validate(data)
            accepted.append(models.Student(**student.model_dump(), school_id=user.school_id))
            seen.add(admission)
        except Exception as exc:
            errors.append({"row": row_number, "error": str(exc)[:400]})
            skipped += 1
    if accepted:
        db.add_all(accepted)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Import conflicted with an existing admission number. No rows were imported; please retry.")
    return {"created": len(accepted), "skipped": skipped, "errors": errors[:100]}

register_crud("students", models.Student, schemas.StudentIn, schemas.StudentOut,
              ("super_admin", "admin", "teacher", "accountant", "transport_manager", "hostel_warden"))
register_crud("staff", models.Staff, schemas.StaffIn, schemas.StaffOut, ADMIN_ROLES)
register_crud("classes", models.SchoolClass, schemas.ClassIn, schemas.ClassOut, ADMIN_ROLES + ("teacher",))
register_crud("vehicles", models.Vehicle, schemas.VehicleIn, schemas.VehicleOut, ADMIN_ROLES + ("transport_manager",))
register_crud("hostels", models.Hostel, schemas.HostelIn, schemas.HostelOut, ADMIN_ROLES + ("hostel_warden",))
register_crud("documents", models.Document, schemas.DocumentIn, schemas.DocumentOut, ADMIN_ROLES + ("accountant", "teacher", "transport_manager", "hostel_warden"))
register_crud("maintenance", models.MaintenanceRequest, schemas.MaintenanceIn, schemas.MaintenanceOut, ADMIN_ROLES + ("transport_manager", "hostel_warden"))
register_crud("fee-structures", models.FeeStructure, schemas.FeeStructureIn, schemas.FeeStructureOut, FINANCE_ROLES)
register_crud("student-fees", models.StudentFee, schemas.StudentFeeIn, schemas.StudentFeeOut, FINANCE_ROLES)

@app.get("/api/schools", response_model=list[schemas.SchoolOut], tags=["schools"])
def list_schools(q: str = Query(default="", max_length=120), db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    stmt = select(models.School).order_by(models.School.name)
    if user.role != "super_admin":
        if not user.school_id:
            raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
        stmt = stmt.where(models.School.id == user.school_id)
    if q:
        stmt = stmt.where(models.School.name.ilike("%" + q + "%"))
    return list(db.scalars(stmt).all())


@app.post("/api/schools", response_model=schemas.SchoolOut, tags=["schools"])
def create_school(payload: schemas.SchoolIn, db: Session = Depends(get_db),
                  user: models.User = Depends(require_roles("super_admin"))):
    school = models.School(name=payload.name.strip(), code=payload.code.strip().upper())
    db.add(school)
    try:
        db.commit()
        db.refresh(school)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="School name or code already exists")
    return school


@app.get("/api/users", response_model=list[schemas.UserOut], tags=["users"])
def list_users(db: Session = Depends(get_db), user: models.User = Depends(require_roles("super_admin", "admin"))):
    stmt = select(models.User).order_by(models.User.id.desc())
    if user.role != "super_admin":
        if not user.school_id:
            raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
        stmt = stmt.where(models.User.school_id == user.school_id)
    return list(db.scalars(stmt).all())


@app.post("/api/users", response_model=schemas.UserOut, tags=["users"])
def create_user(payload: dict, db: Session = Depends(get_db),
                user: models.User = Depends(require_roles("super_admin"))):
    name, email, password, role = payload.get("name"), payload.get("email"), payload.get("password"), payload.get("role", "admin")
    school_id = payload.get("school_id")
    allowed = {"admin", "accountant", "teacher", "transport_manager", "hostel_warden", "student", "parent"}
    if not name or not email or not password or len(password) < 12 or role not in allowed or not school_id:
        raise HTTPException(status_code=422, detail="Name, email, school, role and password of at least 12 characters are required")
    if not db.get(models.School, int(school_id)):
        raise HTTPException(status_code=404, detail="School not found")
    user_obj = models.User(name=name, email=email, password_hash=hash_password(password),
                           role=role, school_id=int(school_id))
    db.add(user_obj)
    try:
        db.commit()
        db.refresh(user_obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    return user_obj



@app.get("/api/fee-reports", tags=["fee-reports"])
def fee_reports(month: int | None = Query(default=None, ge=1, le=12),
                year: int | None = Query(default=None, ge=2000, le=2100),
                school_id: int | None = Query(default=None, gt=0),
                db: Session = Depends(get_db),
                user: models.User = Depends(require_roles("super_admin", "admin", "accountant"))):
    target_school_id = user.school_id if user.role != "super_admin" else school_id
    payment_stmt = select(models.FeePayment, models.Student, models.School).join(
        models.StudentFee, models.FeePayment.student_fee_id == models.StudentFee.id
    ).join(models.Student, models.StudentFee.student_id == models.Student.id).join(
        models.School, models.FeePayment.school_id == models.School.id
    )
    if target_school_id is not None:
        payment_stmt = payment_stmt.where(models.FeePayment.school_id == target_school_id)
    if year:
        payment_stmt = payment_stmt.where(func.extract("year", models.FeePayment.payment_date) == year)
    if month:
        payment_stmt = payment_stmt.where(func.extract("month", models.FeePayment.payment_date) == month)
    payments = db.execute(payment_stmt.order_by(models.FeePayment.payment_date.desc()).limit(100)).all()

    collected_stmt = select(func.coalesce(func.sum(models.FeePayment.amount), 0))
    if target_school_id is not None:
        collected_stmt = collected_stmt.where(models.FeePayment.school_id == target_school_id)
    if year:
        collected_stmt = collected_stmt.where(func.extract("year", models.FeePayment.payment_date) == year)
    if month:
        collected_stmt = collected_stmt.where(func.extract("month", models.FeePayment.payment_date) == month)
    collected = db.scalar(collected_stmt) or 0

    paid_subquery = select(func.coalesce(func.sum(models.FeePayment.amount), 0)).where(
        models.FeePayment.student_fee_id == models.StudentFee.id
    ).correlate(models.StudentFee).scalar_subquery()
    outstanding_stmt = select(func.coalesce(func.sum(
        models.StudentFee.total_amount - models.StudentFee.discount - paid_subquery
    ), 0))
    if target_school_id is not None:
        outstanding_stmt = outstanding_stmt.where(models.StudentFee.school_id == target_school_id)
    if year:
        outstanding_stmt = outstanding_stmt.where(func.extract("year", models.StudentFee.created_at) == year)
    if month:
        outstanding_stmt = outstanding_stmt.where(func.extract("month", models.StudentFee.created_at) == month)
    outstanding = db.scalar(outstanding_stmt) or 0

    chart_stmt = select(
        func.to_char(func.date_trunc("month", models.FeePayment.payment_date), "YYYY-MM"),
        func.sum(models.FeePayment.amount)
    ).group_by(func.date_trunc("month", models.FeePayment.payment_date)).order_by(
        func.date_trunc("month", models.FeePayment.payment_date)
    )
    if target_school_id is not None:
        chart_stmt = chart_stmt.where(models.FeePayment.school_id == target_school_id)
    if year:
        chart_stmt = chart_stmt.where(func.extract("year", models.FeePayment.payment_date) == year)
    chart = [{"period": period, "amount": float(amount or 0)}
             for period, amount in db.execute(chart_stmt).all()]
    recent = [{
        "id": payment.id, "school_name": school.name, "receipt_no": payment.receipt_no,
        "amount": float(payment.amount), "payment_method": payment.payment_method,
        "payment_date": payment.payment_date.isoformat(), "student_name": student.full_name,
        "admission_no": student.admission_no
    } for payment, student, school in payments]
    return {"collected": float(collected), "outstanding": float(outstanding),
            "chart": chart, "recent_payments": recent}


@app.get("/api/fee-dues", tags=["payments"])
def fee_dues(db: Session = Depends(get_db),
             user: models.User = Depends(require_roles("super_admin", "admin", "accountant"))):
    stmt = select(models.StudentFee, models.Student).join(
        models.Student, models.StudentFee.student_id == models.Student.id
    ).order_by(models.Student.full_name)
    if user.role != "super_admin":
        stmt = stmt.where(models.StudentFee.school_id == user.school_id)
    rows = db.execute(stmt).all()
    result = []
    for fee, student in rows:
        paid = db.scalar(select(func.coalesce(func.sum(models.FeePayment.amount), 0)).where(
            models.FeePayment.student_fee_id == fee.id
        )) or 0
        total = Decimal(str(fee.total_amount)) - Decimal(str(fee.discount))
        balance = max(total - Decimal(str(paid)), Decimal("0"))
        if balance > 0:
            result.append({"fee_id": fee.id, "student_name": student.full_name,
                           "admission_no": student.admission_no, "total_amount": float(total),
                           "paid_amount": float(paid), "balance": float(balance)})
    return result


@app.post("/api/student-fees/{fee_id}/payments", response_model=schemas.PaymentOut, tags=["payments"])
def record_payment(fee_id: int, payload: schemas.PaymentIn, db: Session = Depends(get_db),
                   user: models.User = Depends(require_roles("super_admin", "admin", "accountant"))):
    fee = db.get(models.StudentFee, fee_id)
    if not fee or (user.role != "super_admin" and fee.school_id != user.school_id):
        raise HTTPException(status_code=404, detail="Student fee not found")
    already_paid = db.scalar(select(func.coalesce(func.sum(models.FeePayment.amount), 0)).where(models.FeePayment.student_fee_id == fee.id)) or 0
    balance = Decimal(str(fee.total_amount)) - Decimal(str(fee.discount)) - Decimal(str(already_paid))
    if payload.amount > balance:
        raise HTTPException(status_code=422, detail="Payment amount exceeds the outstanding balance")
    payment = models.FeePayment(
        school_id=fee.school_id, student_fee_id=fee.id,
        receipt_no=f"CF-{fee.school_id}-{uuid4().hex[:12].upper()}",
        amount=payload.amount, payment_method=payload.payment_method,
        transaction_reference=payload.transaction_reference, notes=payload.notes,
        payment_date=payload.payment_date or datetime.utcnow(), received_by=user.id
    )
    db.add(payment)
    db.flush()
    paid = db.scalar(select(func.coalesce(func.sum(models.FeePayment.amount), 0)).where(
        models.FeePayment.student_fee_id == fee.id
    )) or 0
    due = Decimal(str(fee.total_amount)) - Decimal(str(fee.discount))
    fee.status = "paid" if Decimal(str(paid)) >= due else "partial"
    db.commit()
    db.refresh(payment)
    return payment



@app.patch("/api/users/{user_id}/school", response_model=schemas.UserOut, tags=["users"])
def assign_user_school(user_id: int, payload: dict, db: Session = Depends(get_db),
                       user: models.User = Depends(require_roles("super_admin"))):
    target = db.get(models.User, user_id)
    school_id = payload.get("school_id")
    if not target or target.role == "super_admin":
        raise HTTPException(status_code=404, detail="School owner account not found")
    if not school_id or not db.get(models.School, int(school_id)):
        raise HTTPException(status_code=404, detail="School not found")
    target.school_id = int(school_id)
    db.commit()
    db.refresh(target)
    return target
