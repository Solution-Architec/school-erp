import os
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, or_
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, get_db, SessionLocal
from . import models, schemas
from .security import hash_password, verify_password, create_access_token, current_user, require_roles

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    return {
        "students": db.scalar(select(func.count()).select_from(models.Student)) or 0,
        "staff": db.scalar(select(func.count()).select_from(models.Staff)) or 0,
        "classes": db.scalar(select(func.count()).select_from(models.SchoolClass)) or 0,
        "vehicles": db.scalar(select(func.count()).select_from(models.Vehicle)) or 0,
        "hostel_rooms": db.scalar(select(func.count()).select_from(models.Hostel)) or 0,
        "open_maintenance": db.scalar(select(func.count()).select_from(models.MaintenanceRequest).where(models.MaintenanceRequest.status == "open")) or 0,
        "user_role": user.role
    }

def register_crud(path, model, schema_in, schema_out, roles):
    def list_items(q: str = Query(default="", max_length=120), limit: int = Query(default=100, ge=1, le=500),
                   offset: int = Query(default=0, ge=0), db: Session = Depends(get_db),
                   user: models.User = Depends(require_roles(*roles))):
        stmt = select(model)
        if q and hasattr(model, "full_name"):
            stmt = stmt.where(model.full_name.ilike(f"%{q}%"))
        elif q and hasattr(model, "name"):
            stmt = stmt.where(model.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(model.id.desc()).offset(offset).limit(limit)
        return list(db.scalars(stmt).all())

    def create_item(payload: Any, db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles(*roles))):
        obj = model(**payload.model_dump())
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
        if not obj:
            raise HTTPException(status_code=404, detail="Record not found")
        return obj

    def update_item(item_id: int, payload: Any, db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles(*roles))):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Record not found")
        for key, value in payload.model_dump().items():
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
        if not obj:
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
register_crud("students", models.Student, schemas.StudentIn, schemas.StudentOut,
              ("super_admin", "admin", "teacher", "accountant", "transport_manager", "hostel_warden"))
register_crud("staff", models.Staff, schemas.StaffIn, schemas.StaffOut, ADMIN_ROLES)
register_crud("classes", models.SchoolClass, schemas.ClassIn, schemas.ClassOut, ADMIN_ROLES + ("teacher",))
register_crud("vehicles", models.Vehicle, schemas.VehicleIn, schemas.VehicleOut, ADMIN_ROLES + ("transport_manager",))
register_crud("hostels", models.Hostel, schemas.HostelIn, schemas.HostelOut, ADMIN_ROLES + ("hostel_warden",))
register_crud("documents", models.Document, schemas.DocumentIn, schemas.DocumentOut, ADMIN_ROLES + ("accountant", "teacher", "transport_manager", "hostel_warden"))
register_crud("maintenance", models.MaintenanceRequest, schemas.MaintenanceIn, schemas.MaintenanceOut, ADMIN_ROLES + ("transport_manager", "hostel_warden"))

@app.get("/api/users", response_model=list[schemas.UserOut], tags=["users"])
def list_users(db: Session = Depends(get_db), user: models.User = Depends(require_roles("super_admin", "admin"))):
    return list(db.scalars(select(models.User).order_by(models.User.id.desc())).all())

@app.post("/api/users", response_model=schemas.UserOut, tags=["users"])
def create_user(payload: dict, db: Session = Depends(get_db),
                user: models.User = Depends(require_roles("super_admin"))):
    name, email, password, role = payload.get("name"), payload.get("email"), payload.get("password"), payload.get("role", "admin")
    allowed = {"super_admin", "admin", "accountant", "teacher", "transport_manager", "hostel_warden", "student", "parent"}
    if not name or not email or not password or len(password) < 12 or role not in allowed:
        raise HTTPException(status_code=422, detail="Name, email, role and password of at least 12 characters are required")
    user_obj = models.User(name=name, email=email, password_hash=hash_password(password), role=role)
    db.add(user_obj)
    try:
        db.commit()
        db.refresh(user_obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    return user_obj
