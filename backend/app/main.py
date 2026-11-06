import os
import secrets
import hashlib
import hmac
import jwt
import smtplib
from email.message import EmailMessage
from datetime import timedelta
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, or_
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, get_db, SessionLocal
from . import models, schemas
from .security import JWT_SECRET_KEY, hash_password, verify_password, create_access_token, current_user, require_roles

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'approved'"))
        tenant_tables = ("students", "staff", "classes", "vehicles", "hostels", "documents", "maintenance_requests", "fee_structures", "student_fees", "fee_payments")
        all_school_tables = ("users",) + tenant_tables
        for table in all_school_tables:
            conn.execute(text('ALTER TABLE "' + table + '" ADD COLUMN IF NOT EXISTS school_id INTEGER REFERENCES schools(id)'))

        # Preserve pre-multi-school records by placing unassigned legacy data
        # into a dedicated school before enforcing tenant isolation constraints.
        conn.execute(text("""
            INSERT INTO schools (name, code, is_active, created_at)
            VALUES ('Migrated Legacy School', 'LEGACY-MIGRATED', TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (code) DO NOTHING
        """))
        legacy_school_id = conn.execute(
            text("SELECT id FROM schools WHERE code = 'LEGACY-MIGRATED'")
        ).scalar_one()
        for table in tenant_tables:
            conn.execute(text(
                'UPDATE "' + table + '" SET school_id = :school_id WHERE school_id IS NULL'
            ), {"school_id": legacy_school_id})
            conn.execute(text(
                'ALTER TABLE "' + table + '" ALTER COLUMN school_id SET NOT NULL'
            ))

        # Super Admin remains global; any legacy school-level users belong to
        # the migrated school until explicitly reassigned in the Schools screen.
        conn.execute(text("""
            UPDATE users SET school_id = :school_id
            WHERE school_id IS NULL AND role <> 'super_admin'
        """), {"school_id": legacy_school_id})

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


# Public account registration and recovery. OTPs are hashed at rest and expire after 10 minutes.
def _otp_digest(email: str, code: str) -> str:
    secret = os.getenv("JWT_SECRET_KEY", "schoolos-development-secret")
    return hashlib.sha256(f"{email.lower()}:{code}:{secret}".encode()).hexdigest()

# Support alerts are throttled per event to avoid flooding the support mailbox.
_support_alert_last_sent: dict[str, datetime] = {}

def _smtp_send_message(msg: EmailMessage) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    if not host or not msg.get("From"):
        raise RuntimeError("SMTP host or sender is not configured")
    port = int(os.getenv("SMTP_PORT", "587"))
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            if username and password:
                server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            if username and password:
                server.login(username, password)
            server.send_message(msg)

def _notify_support(event: str, details: str, throttle_seconds: int = 900) -> None:
    support_email = os.getenv("SUPPORT_EMAIL")
    sender = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USERNAME")
    if not support_email or not sender:
        return
    now = datetime.utcnow()
    previous = _support_alert_last_sent.get(event)
    if previous and (now - previous).total_seconds() < throttle_seconds:
        return
    _support_alert_last_sent[event] = now
    msg = EmailMessage()
    msg["Subject"] = f"SchoolOS support alert: {event}"
    msg["From"] = sender
    msg["To"] = support_email
    msg.set_content(f"SchoolOS authentication alert\\n\\nEvent: {event}\\nDetails: {details}\\nTime (UTC): {now.isoformat()}\\n")
    try:
        _smtp_send_message(msg)
    except Exception as exc:
        # Do not recurse: a broken SMTP connection cannot reliably be reported through itself.
        print(f"SUPPORT ALERT DELIVERY FAILED: {type(exc).__name__}: {exc}")

def _send_auth_code(email: str, code: str, purpose: str) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    sender = os.getenv("SMTP_FROM_EMAIL") or username
    if not host or not sender:
        raise HTTPException(status_code=503, detail="Email delivery is not configured. Contact the platform administrator.")
    msg = EmailMessage()
    msg["Subject"] = {"verify": "SchoolOS email verification", "reset": "SchoolOS password reset", "login_mfa": "Your SchoolOS sign-in verification code"}.get(purpose, "SchoolOS security code")
    msg["From"] = sender
    msg["To"] = email
    action = {"verify": "verify your SchoolOS account", "reset": "reset your SchoolOS password", "login_mfa": "complete your SchoolOS sign-in"}.get(purpose, "verify your SchoolOS identity")
    msg.set_content(f"Your SchoolOS code to {action} is: {code}\\n\\nThis code expires in 10 minutes. If you did not request this, ignore this email.")
    _smtp_send_message(msg)

def _issue_auth_code(db: Session, email: str, purpose: str) -> None:
    now = datetime.utcnow()
    recent = db.scalar(select(models.AuthCode).where(models.AuthCode.email == email,
        models.AuthCode.purpose == purpose, models.AuthCode.created_at > now - timedelta(seconds=60),
        models.AuthCode.used_at.is_(None)).order_by(models.AuthCode.id.desc()))
    if recent:
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting another code")
    code = f"{secrets.randbelow(1000000):06d}"
    db.add(models.AuthCode(email=email, purpose=purpose, code_hash=_otp_digest(email, code),
                           expires_at=now + timedelta(minutes=10)))
    db.commit()
    try:
        _send_auth_code(email, code, purpose)
    except Exception as exc:
        db.rollback()
        _notify_support("OTP email delivery failure", f"Purpose={purpose}; recipient={email}; error={type(exc).__name__}: {exc}")
        raise HTTPException(status_code=503, detail="Could not send email. Check SMTP settings and request a new code.")

def _consume_auth_code(db: Session, email: str, code: str, purpose: str):
    record = db.scalar(select(models.AuthCode).where(models.AuthCode.email == email,
        models.AuthCode.purpose == purpose, models.AuthCode.used_at.is_(None))
        .order_by(models.AuthCode.id.desc()))
    if not record or record.expires_at < datetime.utcnow() or record.attempts >= 5:
        if record and record.attempts >= 5:
            _notify_support("OTP attempt limit reached", f"Purpose={purpose}; account email={email}; maximum incorrect attempts reached.")
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    record.attempts += 1
    if not hmac.compare_digest(record.code_hash, _otp_digest(email, code)):
        attempts = record.attempts
        db.commit()
        if attempts >= 5:
            _notify_support("Repeated incorrect OTP", f"Purpose={purpose}; account email={email}; five incorrect codes entered.")
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    record.used_at = datetime.utcnow()
    db.commit()

@app.post("/api/auth/register-school", tags=["auth"])
def register_school(payload: dict, db: Session = Depends(get_db)):
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    school_name = str(payload.get("school_name", "")).strip()
    school_code = str(payload.get("school_code", "")).strip().upper()
    if not all((name, email, password, school_name, school_code)) or len(password) < 12:
        raise HTTPException(status_code=422, detail="All fields are required and password must be at least 12 characters")
    if db.scalar(select(models.User.id).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    school = models.School(name=school_name, code=school_code)
    db.add(school)
    try:
        db.flush()
        account = models.User(name=name, email=email, password_hash=hash_password(password), role="principal",
            school_id=school.id, is_active=False, email_verified=False, approval_status="approved")
        db.add(account)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="School name/code or email already exists")
    _issue_auth_code(db, email, "verify")
    return {"message": "School registered. Verify the email address to activate your Principal account.", "email": email}

@app.post("/api/auth/register-staff", tags=["auth"])
def register_staff(payload: dict, db: Session = Depends(get_db)):
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    school_code = str(payload.get("school_code", "")).strip().upper()
    role = str(payload.get("role", "principal")).strip().lower()
    allowed = {"principal", "vice_principal", "teacher", "account", "clerk", "office_assistant",
               "librarian", "lab_assistant", "it_administrator", "transport_manager",
               "hostel_warden", "security_guard", "others", "user", "admin", "accountant", "student", "parent"}
    if not all((name, email, password, school_code)) or len(password) < 12 or role not in allowed:
        raise HTTPException(status_code=422, detail="Provide all fields, a valid account type and a password of at least 12 characters")
    role = "parent" if role == "parent" else role
    school = db.scalar(select(models.School).where(models.School.code == school_code, models.School.is_active.is_(True)))
    if not school:
        raise HTTPException(status_code=404, detail="School code not found")
    if db.scalar(select(models.User.id).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    account = models.User(name=name, email=email, password_hash=hash_password(password), role=role,
        school_id=school.id, is_active=False, email_verified=False, approval_status="pending")
    db.add(account)
    db.commit()
    _issue_auth_code(db, email, "verify")
    return {"message": "Registration received. Verify your email; an authorized school user must approve the account.", "email": email}

@app.post("/api/auth/verify-email", tags=["auth"])
def verify_email(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    account = db.scalar(select(models.User).where(models.User.email == email))
    if not account:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    _consume_auth_code(db, email, code, "verify")
    account.email_verified = True
    if account.approval_status == "approved":
        account.is_active = True
    db.commit()
    return {"message": "Email verified. " + ("You can now sign in." if account.is_active else "Your school must approve your account before sign-in.")}

@app.post("/api/auth/resend-verification", tags=["auth"])
def resend_verification(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    account = db.scalar(select(models.User).where(models.User.email == email))
    if account and not account.email_verified:
        _issue_auth_code(db, email, "verify")
    return {"message": "If verification is pending, a new code has been sent."}

@app.post("/api/auth/forgot-password", tags=["auth"])
def forgot_password(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    account = db.scalar(select(models.User).where(models.User.email == email, models.User.email_verified.is_(True)))
    if account:
        _issue_auth_code(db, email, "reset")
    return {"message": "If a verified account exists for this email, a reset code has been sent."}

@app.post("/api/auth/reset-password", tags=["auth"])
def reset_password(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    password = str(payload.get("password", ""))
    if len(password) < 12:
        raise HTTPException(status_code=422, detail="Password must be at least 12 characters")
    account = db.scalar(select(models.User).where(models.User.email == email))
    if not account:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    _consume_auth_code(db, email, code, "reset")
    account.password_hash = hash_password(password)
    db.commit()
    return {"message": "Password updated. You can now sign in."}

@app.get("/api/auth/pending-users", tags=["auth"])
def pending_users(db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    return list(db.scalars(select(models.User).where(models.User.school_id == user.school_id,
        models.User.approval_status == "pending", models.User.email_verified.is_(True)).order_by(models.User.created_at)).all())

@app.post("/api/auth/users/{user_id}/approval", tags=["auth"])
def approve_user(user_id: int, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(require_roles("admin"))):
    target = db.get(models.User, user_id)
    decision = str(payload.get("decision", "")).lower()
    if not target or target.school_id != user.school_id or target.role == "super_admin":
        raise HTTPException(status_code=404, detail="Pending staff account not found")
    if decision not in ("approve", "reject") or not target.email_verified:
        raise HTTPException(status_code=422, detail="A verified account and approve/reject decision are required")
    target.approval_status = "approved" if decision == "approve" else "rejected"
    target.is_active = decision == "approve"
    db.commit()
    return {"message": "Account " + ("approved" if decision == "approve" else "rejected")}

DEMO_LOGIN_EMAILS = {
    "demo.developer@jovoo.in", "demo.principal@jovoo.in",
    "demo.viceprincipal@jovoo.in", "demo.teacher@jovoo.in",
    "demo.accounts@jovoo.in", "demo.clerk@jovoo.in",
    "demo.officeassistant@jovoo.in", "demo.librarian@jovoo.in",
    "demo.labassistant@jovoo.in", "demo.itadmin@jovoo.in",
    "demo.transport@jovoo.in", "demo.warden@jovoo.in",
    "demo.security@jovoo.in", "demo.others@jovoo.in",
    "demo.parent@jovoo.in",
}


def _demo_login_enabled(email: str) -> bool:
    return os.getenv("ENABLE_DEMO_LOGIN", "false").lower() == "true" and email.lower() in DEMO_LOGIN_EMAILS


@app.post("/api/auth/login", tags=["auth"])
def login(payload: schemas.LoginInput, db: Session = Depends(get_db)):
    school_code = (payload.school_code or "").strip().upper()
    email = str(payload.email).strip().lower()
    # A blank school code is accepted only for the global Super Admin account.
    # Tenant users must provide an active school's code; no tenant lookup is
    # attempted without it. The configured platform code remains supported.
    platform_code = os.getenv("PLATFORM_SCHOOL_CODE", "PLATFORM").strip().upper()
    if not school_code:
        user = db.scalar(select(models.User).where(
            models.User.email == email, models.User.role == "super_admin",
            models.User.school_id.is_(None)))
    else:
        school = db.scalar(select(models.School).where(
            models.School.code == school_code, models.School.is_active.is_(True)))
        if school:
            user = db.scalar(select(models.User).where(
                models.User.email == email, models.User.school_id == school.id))
        elif school_code == platform_code:
            user = db.scalar(select(models.User).where(
                models.User.email == email, models.User.role == "super_admin",
                models.User.school_id.is_(None)))
        else:
            user = None
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid school code, email or password")
    demo_login = _demo_login_enabled(user.email)
    if not user.email_verified and not demo_login:
        raise HTTPException(status_code=403, detail="Verify your email before signing in")
    # Demo-only accounts may skip email verification when the explicit testing flag is enabled.
    if demo_login and not user.email_verified:
        user.email_verified = True
        db.commit()
    if user.approval_status == "pending":
        raise HTTPException(status_code=403, detail="Your school has not approved your account yet")
    if user.approval_status == "rejected" or not user.is_active:
        raise HTTPException(status_code=403, detail="This account is inactive. Contact your school")
    if user.role != "parent" and not demo_login:
        _issue_auth_code(db, email, "login_mfa")
        challenge = jwt.encode({
            "sub": str(user.id), "purpose": "login_mfa",
            "exp": datetime.utcnow() + timedelta(minutes=5)
        }, JWT_SECRET_KEY, algorithm="HS256")
        return {"mfa_required": True, "mfa_token": challenge,
                "message": "A sign-in verification code has been sent to your email."}
    return {"access_token": create_access_token(user), "token_type": "bearer",
            "user": schemas.UserOut.model_validate(user).model_dump()}


DEMO_PREVIEW_USERS = {
    "principal": ("demo.principal@jovoo.in", "principal"),
    "vice_principal": ("demo.viceprincipal@jovoo.in", "vice_principal"),
    "teacher": ("demo.teacher@jovoo.in", "teacher"),
    "account": ("demo.accounts@jovoo.in", "account"),
    "clerk": ("demo.clerk@jovoo.in", "clerk"),
    "office_assistant": ("demo.officeassistant@jovoo.in", "office_assistant"),
    "librarian": ("demo.librarian@jovoo.in", "librarian"),
    "lab_assistant": ("demo.labassistant@jovoo.in", "lab_assistant"),
    "it_administrator": ("demo.itadmin@jovoo.in", "it_administrator"),
    "transport_manager": ("demo.transport@jovoo.in", "transport_manager"),
    "hostel_warden": ("demo.warden@jovoo.in", "hostel_warden"),
    "security_guard": ("demo.security@jovoo.in", "security_guard"),
    "others": ("demo.others@jovoo.in", "others"),
    "parent": ("demo.parent@jovoo.in", "parent"),
}


@app.post("/api/dev/demo-role-preview/{role}", tags=["developer-tools"])
def preview_demo_role(
    role: str,
    db: Session = Depends(get_db),
    developer: models.User = Depends(require_roles("super_admin")),
):
    """Issue a real demo-account token only to a Developer when demo login is enabled."""
    if os.getenv("ENABLE_DEMO_LOGIN", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Demo role preview is disabled")
    if role not in DEMO_PREVIEW_USERS:
        raise HTTPException(status_code=404, detail="Demo role not found")
    email, expected_role = DEMO_PREVIEW_USERS[role]
    target = db.scalar(select(models.User).where(models.User.email == email))
    if (not target or target.role != expected_role or not target.is_active
            or not target.email_verified or target.approval_status != "approved"):
        raise HTTPException(status_code=404, detail="Active seeded demo account not found")
    if not target.school_id or not db.scalar(select(models.School.id).where(
            models.School.id == target.school_id, models.School.is_active.is_(True))):
        raise HTTPException(status_code=404, detail="Demo school is unavailable")
    return {
        "access_token": create_access_token(target),
        "token_type": "bearer",
        "user": schemas.UserOut.model_validate(target).model_dump(),
    }


@app.post("/api/auth/verify-mfa", tags=["auth"])
def verify_login_mfa(payload: dict, db: Session = Depends(get_db)):
    challenge = str(payload.get("mfa_token", ""))
    code = str(payload.get("code", "")).strip()
    try:
        claims = jwt.decode(challenge, JWT_SECRET_KEY,
                            algorithms=["HS256"])
        if claims.get("purpose") != "login_mfa":
            raise ValueError("Wrong challenge purpose")
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Sign-in challenge expired. Please sign in again.")
    user = db.get(models.User, user_id)
    if not user or not user.is_active or not user.email_verified or user.role == "parent":
        raise HTTPException(status_code=401, detail="Account is not eligible for this sign-in challenge")
    _consume_auth_code(db, user.email, code, "login_mfa")
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
    if user.role == "parent":
        return {"students": 0, "staff": 0, "classes": 0, "vehicles": 0,
                "hostel_rooms": 0, "open_maintenance": 0, "user_role": "parent"}

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
        if user.role != "super_admin" and not user.school_id:
            raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
        values = payload.model_dump()
        create_staff_account = False
        account_role = None
        account_password = None
        if model is models.Staff:
            create_staff_account = values.pop("create_account", False)
            account_role = values.pop("account_role", "principal")
            account_password = values.pop("account_password", None)
            if create_staff_account:
                if user.role != "super_admin":
                    raise HTTPException(status_code=403, detail="Only Developer can create staff login accounts")
                if account_role not in ("principal", "vice_principal", "teacher", "account", "clerk",
                                        "office_assistant", "librarian", "lab_assistant", "it_administrator",
                                        "transport_manager", "hostel_warden", "security_guard", "others",
                                        "user", "admin", "accountant", "parent"):
                    raise HTTPException(status_code=422, detail="Select a valid school role or Parent")
                if not account_password or len(account_password) < 12:
                    raise HTTPException(status_code=422, detail="Set a login password with at least 12 characters")
                if db.scalar(select(models.User.id).where(models.User.email == values.get("email", "").lower())):
                    raise HTTPException(status_code=409, detail="A login account already exists for this email")
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
            if create_staff_account:
                db.add(models.User(
                    name=values["full_name"],
                    email=values["email"].strip().lower(),
                    password_hash=hash_password(account_password),
                    role=account_role,
                    school_id=values["school_id"],
                    is_active=True,
                    email_verified=True,
                    approval_status="approved",
                ))
            db.commit()
            db.refresh(obj)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Duplicate staff employee number or login email")
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
        if model is models.Staff:
            if values.pop("create_account", False) or values.pop("account_password", None):
                raise HTTPException(status_code=422, detail="Create login accounts when adding a staff record, not while editing")
            values.pop("account_role", None)
        validate_related_records(values, user, db)
        if model is models.Staff:
            # Standard users can never move staff outside their assigned school.
            if user.role != "super_admin":
                values["school_id"] = user.school_id
            elif not values.get("school_id"):
                values["school_id"] = obj.school_id
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


STANDARD_ROLES = ("user", "admin", "accountant", "teacher", "transport_manager", "hostel_warden", "student")
ADMIN_ROLES = ("super_admin",) + STANDARD_ROLES
FINANCE_ROLES = ADMIN_ROLES
@app.post("/api/students/import", tags=["students"])
async def import_students(file: UploadFile = File(...), school_id: int | None = Form(default=None),
                         db: Session = Depends(get_db),
                         user: models.User = Depends(require_roles("super_admin", "admin"))):
    if user.role == "super_admin":
        target_school_id = school_id
        if not target_school_id or not db.get(models.School, target_school_id):
            raise HTTPException(status_code=422, detail="Select a valid school before importing students")
    else:
        if not user.school_id:
            raise HTTPException(status_code=403, detail="Assign your account to a school before importing students")
        target_school_id = user.school_id
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
    existing_stmt = select(models.Student.admission_no).where(models.Student.school_id == target_school_id)
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
            accepted.append(models.Student(**student.model_dump(), school_id=target_school_id))
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
    return {"school_id": target_school_id, "created": len(accepted), "skipped": skipped, "errors": errors[:100]}

register_crud("students", models.Student, schemas.StudentIn, schemas.StudentOut, ADMIN_ROLES)
register_crud("staff", models.Staff, schemas.StaffIn, schemas.StaffOut, ADMIN_ROLES)
register_crud("classes", models.SchoolClass, schemas.ClassIn, schemas.ClassOut, ADMIN_ROLES)
register_crud("vehicles", models.Vehicle, schemas.VehicleIn, schemas.VehicleOut, ADMIN_ROLES)
register_crud("hostels", models.Hostel, schemas.HostelIn, schemas.HostelOut, ADMIN_ROLES)
register_crud("documents", models.Document, schemas.DocumentIn, schemas.DocumentOut, ADMIN_ROLES)
register_crud("maintenance", models.MaintenanceRequest, schemas.MaintenanceIn, schemas.MaintenanceOut, ADMIN_ROLES)
register_crud("fee-structures", models.FeeStructure, schemas.FeeStructureIn, schemas.FeeStructureOut, FINANCE_ROLES)
register_crud("student-fees", models.StudentFee, schemas.StudentFeeIn, schemas.StudentFeeOut, FINANCE_ROLES)


# Shared CSV/XLSX import for operational modules. Financial payments and private
# document files remain dedicated workflows to preserve receipt and storage integrity.
@app.post("/api/{resource}/import", tags=["data-import"])
async def import_module_records(
    resource: str,
    file: UploadFile = File(...),
    school_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin", "admin")),
):
    import csv
    import io

    importable = {
        "staff": (models.Staff, schemas.StaffIn, ("employee_no",)),
        "classes": (models.SchoolClass, schemas.ClassIn, ("name", "section", "academic_year")),
        "vehicles": (models.Vehicle, schemas.VehicleIn, ("registration_no",)),
        "hostels": (models.Hostel, schemas.HostelIn, ("name", "room_no")),
        "maintenance": (models.MaintenanceRequest, schemas.MaintenanceIn, ()),
        "fee-structures": (models.FeeStructure, schemas.FeeStructureIn, ("name", "academic_year", "term")),
    }
    if resource not in importable:
        raise HTTPException(status_code=404, detail="Bulk import is not enabled for this module")
    if user.role == "super_admin":
        target_school_id = school_id
        if not target_school_id or not db.get(models.School, target_school_id):
            raise HTTPException(status_code=422, detail="Select a valid school before importing")
    else:
        if not user.school_id:
            raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
        target_school_id = user.school_id

    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="Upload a .csv or .xlsx file")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")
    try:
        if filename.endswith(".csv"):
            records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        else:
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            sheet = workbook.active
            iterator = sheet.iter_rows(values_only=True)
            headers = [str(value).strip() if value is not None else "" for value in next(iterator, ())]
            records = [dict(zip(headers, row)) for row in iterator if any(value is not None for value in row)]
            workbook.close()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read import file: {exc}")
    if not records:
        raise HTTPException(status_code=400, detail="The import file contains no data rows")
    if len(records) > 5000:
        raise HTTPException(status_code=400, detail="Maximum 5,000 rows per import")

    model, schema, identity_fields = importable[resource]
    allowed = set(schema.model_fields.keys()) - {"school_id"}
    existing = set()
    if identity_fields:
        stmt = select(model).where(model.school_id == target_school_id)
        for item in db.scalars(stmt).all():
            existing.add(tuple(str(getattr(item, field) or "").strip().casefold() for field in identity_fields))

    accepted, errors, seen = [], [], set()
    skipped = 0
    for row_number, source in enumerate(records, start=2):
        normalized = {str(key).strip().lower(): value for key, value in source.items() if key is not None}
        values = {key: value for key, value in normalized.items() if key in allowed and value is not None and value != ""}
        try:
            parsed = schema.model_validate(values)
            payload = parsed.model_dump()
            payload["school_id"] = target_school_id
            if identity_fields:
                identity = tuple(str(payload.get(field) or "").strip().casefold() for field in identity_fields)
                if any(not value for value in identity):
                    raise ValueError("Required duplicate-check fields are missing: " + ", ".join(identity_fields))
                if identity in existing or identity in seen:
                    skipped += 1
                    errors.append({"row": row_number, "error": "Duplicate record skipped"})
                    continue
                seen.add(identity)
            accepted.append(model(**payload))
        except Exception as exc:
            skipped += 1
            errors.append({"row": row_number, "error": str(exc)[:400]})

    if accepted:
        db.add_all(accepted)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Import conflicted with existing records; no rows were imported. Review duplicates and retry.")
    return {"resource": resource, "school_id": target_school_id, "created": len(accepted),
            "skipped": skipped, "errors": errors[:100]}

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
def list_users(db: Session = Depends(get_db), user: models.User = Depends(require_roles("super_admin"))):
    stmt = select(models.User).order_by(models.User.id.desc())
    if user.role != "super_admin":
        if not user.school_id:
            raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
        stmt = stmt.where(models.User.school_id == user.school_id)
    return list(db.scalars(stmt).all())


@app.post("/api/users", response_model=schemas.UserOut, tags=["users"])
def create_user(payload: dict, db: Session = Depends(get_db),
                user: models.User = Depends(require_roles("super_admin"))):
    name, email, password, role = payload.get("name"), payload.get("email"), payload.get("password"), payload.get("role", "user")
    school_id = payload.get("school_id")
    allowed = {"user", "parent"}
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
    if user.role != "super_admin" and not user.school_id:
        raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
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

    chart_year = func.extract("year", models.FeePayment.payment_date)
    chart_month = func.extract("month", models.FeePayment.payment_date)

    chart_stmt = select(
        chart_year.label("year"),
        chart_month.label("month"),
        func.sum(models.FeePayment.amount)
    ).group_by(
        chart_year, chart_month
    ).order_by(
        chart_year, chart_month
    )
    if target_school_id is not None:
        chart_stmt = chart_stmt.where(models.FeePayment.school_id == target_school_id)
    if year:
        chart_stmt = chart_stmt.where(chart_year == year)
    chart = [
        {
            "period": f"{int(payment_year):04d}-{int(payment_month):02d}",
            "amount": float(amount or 0)
        }
        for payment_year, payment_month, amount in db.execute(chart_stmt).all()
    ]
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
    if user.role != "super_admin" and not user.school_id:
        raise HTTPException(status_code=403, detail="Your account is not assigned to a school")
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


# Parent App / family portal
@app.post("/api/parent-links", tags=["parent-portal"])
def create_parent_link(payload: dict, db: Session = Depends(get_db),
                       user: models.User = Depends(require_roles("super_admin", "admin"))):
    parent_id = payload.get("parent_user_id")
    student_id = payload.get("student_id")
    relationship = str(payload.get("relationship", "parent"))[:40]
    if not parent_id or not student_id:
        raise HTTPException(status_code=422, detail="parent_user_id and student_id are required")
    parent = db.get(models.User, int(parent_id))
    student = db.get(models.Student, int(student_id))
    if not parent or parent.role != "parent":
        raise HTTPException(status_code=404, detail="Parent account not found")
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if parent.school_id != student.school_id:
        raise HTTPException(status_code=422, detail="Parent and student must belong to the same school")
    if user.role != "super_admin" and (user.school_id != parent.school_id or user.school_id != student.school_id):
        raise HTTPException(status_code=404, detail="Parent or student not found in your school")
    link = models.ParentStudentLink(school_id=student.school_id, parent_user_id=parent.id,
                                    student_id=student.id, relationship=relationship)
    db.add(link)
    try:
        db.commit()
        db.refresh(link)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Parent is already linked to this student")
    return {"id": link.id, "parent_user_id": parent.id, "student_id": student.id,
            "school_id": link.school_id, "relationship": link.relationship, "is_active": link.is_active}


@app.get("/api/parent/children", tags=["parent-portal"])
def parent_children(db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles("parent"))):
    stmt = select(models.Student, models.ParentStudentLink).join(
        models.ParentStudentLink, models.ParentStudentLink.student_id == models.Student.id
    ).where(models.ParentStudentLink.parent_user_id == user.id,
             models.ParentStudentLink.school_id == user.school_id,
             models.ParentStudentLink.is_active.is_(True),
             models.Student.school_id == user.school_id)
    return [{"id": student.id, "admission_no": student.admission_no, "full_name": student.full_name,
             "class_name": student.class_name, "section": student.section, "status": student.status,
             "relationship": link.relationship}
            for student, link in db.execute(stmt).all()]


@app.get("/api/parent/children/{student_id}/fees", tags=["parent-portal"])
def parent_child_fees(student_id: int, db: Session = Depends(get_db),
                      user: models.User = Depends(require_roles("parent"))):
    allowed = db.scalar(select(models.ParentStudentLink.id).where(
        models.ParentStudentLink.parent_user_id == user.id,
        models.ParentStudentLink.student_id == student_id,
        models.ParentStudentLink.school_id == user.school_id,
        models.ParentStudentLink.is_active.is_(True)))
    if not allowed:
        raise HTTPException(status_code=404, detail="Student not found")
    fees = db.scalars(select(models.StudentFee).where(
        models.StudentFee.student_id == student_id,
        models.StudentFee.school_id == user.school_id).order_by(models.StudentFee.id.desc())).all()
    result = []
    for fee in fees:
        paid = db.scalar(select(func.coalesce(func.sum(models.FeePayment.amount), 0)).where(
            models.FeePayment.student_fee_id == fee.id,
            models.FeePayment.school_id == user.school_id)) or 0
        due = max(Decimal(str(fee.total_amount)) - Decimal(str(fee.discount)) - Decimal(str(paid)), Decimal("0"))
        result.append({"fee_id": fee.id, "category": fee.category, "description": fee.description,
                       "academic_year": fee.academic_year, "term": fee.term,
                       "total": float(Decimal(str(fee.total_amount)) - Decimal(str(fee.discount))),
                       "paid": float(paid), "balance": float(due), "status": fee.status,
                       "due_date": fee.due_date.isoformat() if fee.due_date else None})
    return result


# Safe FAQ assistant: answers only approved school help topics, no student-specific data.
@app.post("/api/chatbot/faq", tags=["chatbot"])
def chatbot_faq(payload: dict, user: models.User = Depends(current_user)):
    question = str(payload.get("question", "")).strip().lower()
    if not question or len(question) > 500:
        raise HTTPException(status_code=422, detail="Question must be between 1 and 500 characters")
    topics = [
        (("fee", "payment", "tuition", "receipt"), "For fee balances and receipts, open Finance → Student Fees or Fee Reports. Parents can view linked students’ balances in the Parent Portal. Payment gateway processing is not enabled yet."),
        (("admission", "enroll", "enrollment"), "Admissions are managed from Students → Add Student. Please contact your school office for required documents and admission dates."),
        (("transport", "bus", "route"), "Transport routes and vehicle details are maintained in the Transport module. Contact your school transport manager for route allocation."),
        (("hostel", "room", "boarding"), "Hostel occupancy and room records are maintained in the Hostel module. Contact your school hostel warden for availability."),
        (("attendance", "absent", "present"), "Attendance tracking is planned but is not yet available in this release. Please contact your class teacher for attendance records."),
        (("timetable", "schedule", "class time"), "Timetable management is planned for a future release. Please contact the academic office for the current timetable."),
        (("password", "login", "sign in", "account"), "If you cannot sign in, contact your school administrator to reset or reactivate your account. Never share your password or OTP."),
    ]
    for keywords, answer in topics:
        if any(keyword in question for keyword in keywords):
            return {"answer": answer, "source": "schoolos-approved-faq", "needs_human_support": False}
    return {"answer": "I couldn't find an approved answer for that question. Please contact your school office or administrator.", "source": "schoolos-approved-faq", "needs_human_support": True}
