import os
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import get_db
from .models import User, RolePermission
from .security_config import load_jwt_secret

# Fail closed during application import/startup: there is no development fallback.
JWT_SECRET_KEY = load_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
password_hash = PasswordHash.recommended()
DEFAULT_ROLE_MODULES = {
    "user": ["dashboard", "chatbot", "approvals", "students", "staff", "classes", "vehicles", "hostels", "documents", "maintenance", "fee-structures", "student-fees", "payments", "fee-reports", "attendance", "timetable", "exams", "report-cards", "homework", "student-leave", "parent-messages", "library-books", "library-loans"],
    "admin": ["dashboard", "chatbot", "approvals", "students", "staff", "classes", "vehicles", "hostels", "documents", "maintenance", "fee-structures", "student-fees", "payments", "fee-reports", "attendance", "timetable", "exams", "report-cards", "homework", "student-leave", "parent-messages", "library-books", "library-loans"],
    "principal": ["dashboard", "chatbot", "approvals", "students", "staff", "classes", "vehicles", "hostels", "documents", "maintenance", "fee-structures", "student-fees", "payments", "fee-reports", "attendance", "timetable", "exams", "report-cards", "homework", "student-leave", "parent-messages", "library-books", "library-loans"],
    "vice_principal": ["dashboard", "chatbot", "students", "staff", "classes", "documents", "maintenance", "fee-reports", "attendance", "timetable", "exams", "report-cards", "homework", "student-leave", "parent-messages", "library-books", "library-loans"],
    "teacher": ["dashboard", "chatbot", "students", "classes", "documents", "attendance", "timetable", "exams", "report-cards", "homework", "student-leave", "parent-messages"],
    "account": ["dashboard", "chatbot", "students", "fee-structures", "student-fees", "payments", "fee-reports"],
    "accountant": ["dashboard", "chatbot", "students", "fee-structures", "student-fees", "payments", "fee-reports"],
    "clerk": ["dashboard", "chatbot", "students", "student-fees", "payments", "documents"],
    "office_assistant": ["dashboard", "chatbot", "students", "staff", "documents"],
    "librarian": ["dashboard", "chatbot", "students", "documents", "library-books", "library-loans"],
    "lab_assistant": ["dashboard", "chatbot", "documents", "maintenance"],
    "it_administrator": ["dashboard", "chatbot", "staff", "documents", "maintenance"],
    "transport_manager": ["dashboard", "chatbot", "students", "vehicles", "documents", "maintenance"],
    "hostel_warden": ["dashboard", "chatbot", "students", "hostels", "documents", "maintenance"],
    "security_guard": ["dashboard", "chatbot", "students"],
    "others": ["dashboard", "chatbot"],
    "parent": ["parent-portal", "chatbot", "student-leave", "parent-messages"],
}


ROLE_CREATE_MODULES = {
    "user": DEFAULT_ROLE_MODULES["user"],
    "admin": DEFAULT_ROLE_MODULES["admin"],
    "principal": DEFAULT_ROLE_MODULES["principal"],
    "vice_principal": [m for m in DEFAULT_ROLE_MODULES["vice_principal"] if m != "fee-reports"],
    "teacher": ["attendance", "report-cards", "homework", "student-leave", "parent-messages"],
    "account": ["fee-structures", "student-fees", "payments"],
    "accountant": ["fee-structures", "student-fees", "payments"],
    "clerk": ["students", "student-fees", "payments", "documents"],
    "office_assistant": ["students", "documents"],
    "librarian": ["library-books", "library-loans", "documents"],
    "lab_assistant": ["maintenance", "documents"],
    "it_administrator": ["staff", "documents", "maintenance"],
    "transport_manager": ["vehicles", "documents", "maintenance"],
    "hostel_warden": ["hostels", "documents", "maintenance"],
    "parent": ["student-leave", "parent-messages"],
}
ROLE_EDIT_MODULES = {
    **ROLE_CREATE_MODULES,
    "teacher": ["attendance", "report-cards", "homework", "student-leave"],
    "account": ["fee-structures", "student-fees"],
    "accountant": ["fee-structures", "student-fees"],
    "clerk": ["students", "student-fees", "documents"],
    "librarian": ["library-books", "library-loans", "documents"],
    "parent": [],
}
NON_DELETABLE_MODULES = {
    "dashboard", "parent-portal", "chatbot", "approvals", "schools",
    "payments", "fee-reports", "parent-messages", "library-loans",
}


def default_module_permission(role: str, module_key: str, action: str) -> bool:
    """Return the least-privilege default used by both the API and RBAC editor."""
    if module_key not in DEFAULT_ROLE_MODULES.get(role, []):
        return False
    if action == "View":
        return True
    if action == "Create":
        return module_key in ROLE_CREATE_MODULES.get(role, [])
    if action == "Edit":
        return module_key in ROLE_EDIT_MODULES.get(role, [])
    # Generic CRUD deletion is intentionally admin-only and unavailable for
    # workflow/history endpoints that do not support deletion.
    if action == "Delete":
        return role == "admin" and module_key not in NON_DELETABLE_MODULES
    if action == "Approve" and module_key == "approvals":
        return role in {"admin", "principal", "vice_principal", "user"}
    if action == "Approve" and module_key == "student-leave":
        return role in {"admin", "principal", "vice_principal", "teacher", "user"}
    # Export is opt-in; it requires an explicit permission grant.
    return False
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role, "iat": now,
               "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token",
                            headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or does not exist")
    return user

def require_roles(*roles: str):
    """Authorize only the explicitly listed roles; never broaden an admin grant."""
    def checker(user: User = Depends(current_user)) -> User:
        if user.role in roles:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker


def require_module_permission(module_key: str, action: str, *fallback_roles: str):
    """Apply explicit RBAC overrides, then least-privilege defaults intersected with route policy."""
    def checker(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if user.role == "super_admin":
            return user
        school_grant = None
        if user.school_id is not None:
            school_grant = db.scalar(select(RolePermission).where(
                RolePermission.role == user.role,
                RolePermission.school_id == user.school_id,
                RolePermission.module_key == module_key,
                RolePermission.action == action,
            ))
        grant = school_grant or db.scalar(select(RolePermission).where(
            RolePermission.role == user.role,
            RolePermission.school_id.is_(None),
            RolePermission.module_key == module_key,
            RolePermission.action == action,
        ))
        # Explicit grants intentionally override the route's legacy fallback role list.
        if grant is not None:
            if grant.enabled:
                return user
            raise HTTPException(status_code=403, detail=f"Permission denied: {module_key} / {action}")
        # Until an administrator configures a custom matrix, defaults are not a
        # permissive fallback: they must also satisfy the route's own role policy.
        if user.role not in fallback_roles or not default_module_permission(user.role, module_key, action):
            raise HTTPException(status_code=403, detail=f"Permission denied: {module_key} / {action}")
        return user
    return checker
