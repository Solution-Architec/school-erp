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

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "unsafe-development-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
password_hash = PasswordHash.recommended()
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


STANDARD_USER_ROLES = {
    "user", "admin", "accountant", "teacher", "transport_manager", "hostel_warden", "student",
    "principal", "vice_principal", "account", "clerk", "office_assistant", "librarian",
    "lab_assistant", "it_administrator", "security_guard", "others"
}


def require_roles(*roles: str):
    """Authorize only the exact roles listed by a route.

    School operational access must use require_module_permission so that every
    module/action is checked against the role permission matrix.
    """
    def checker(user: User = Depends(current_user)) -> User:
        if user.role in roles:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker


# Secure system defaults used when neither a school override nor an ERP-wide
# RolePermission row exists. View is deliberately separated from write actions.
# A missing role/module/action entry is always denied.
_VIEW_ONLY = {"View"}
_VIEW_CREATE_EDIT = {"View", "Create", "Edit"}
_LEADERSHIP_MODULES = {
    "dashboard", "chatbot", "students", "staff", "classes", "vehicles",
    "hostels", "documents", "maintenance", "fee-structures", "student-fees",
    "payments", "fee-reports",
}
DEFAULT_ROLE_PERMISSIONS: dict[str, dict[str, set[str]]] = {
    "user": {**{m: set(_VIEW_CREATE_EDIT) for m in _LEADERSHIP_MODULES}, "approvals": {"View", "Approve"}},
    "admin": {**{m: set(_VIEW_CREATE_EDIT) for m in _LEADERSHIP_MODULES}, "approvals": {"View", "Approve"}},
    "principal": {**{m: set(_VIEW_CREATE_EDIT) for m in _LEADERSHIP_MODULES}, "approvals": {"View", "Approve"}},
    "vice_principal": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "fee-reports")},
        **{m: set(_VIEW_CREATE_EDIT) for m in ("students", "staff", "classes", "documents", "maintenance")},
    },
    "teacher": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "classes", "documents")},
    },
    "account": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "fee-reports")},
        **{m: set(_VIEW_CREATE_EDIT) for m in ("fee-structures", "student-fees")},
        "payments": {"View", "Create"},
    },
    "accountant": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "fee-reports")},
        **{m: set(_VIEW_CREATE_EDIT) for m in ("fee-structures", "student-fees")},
        "payments": {"View", "Create"},
    },
    "clerk": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "documents")},
        "student-fees": {"View", "Create", "Edit"},
        "payments": {"View", "Create"},
    },
    "office_assistant": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "approvals")},
        **{m: set(_VIEW_CREATE_EDIT) for m in ("students", "staff", "documents")},
    },
    "librarian": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "documents")},
    },
    "lab_assistant": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "documents")},
        "maintenance": set(_VIEW_CREATE_EDIT),
    },
    "it_administrator": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "staff", "documents", "approvals")},
        "maintenance": set(_VIEW_CREATE_EDIT),
    },
    "transport_manager": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "documents")},
        **{m: set(_VIEW_CREATE_EDIT) for m in ("vehicles", "maintenance")},
    },
    "hostel_warden": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students", "documents")},
        **{m: set(_VIEW_CREATE_EDIT) for m in ("hostels", "maintenance")},
    },
    "security_guard": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot", "students")},
    },
    "others": {
        **{m: set(_VIEW_ONLY) for m in ("dashboard", "chatbot")},
    },
    "parent": {
        **{m: set(_VIEW_ONLY) for m in ("parent-portal", "chatbot")},
    },
}


def default_role_permission(role: str, module_key: str, action: str) -> bool:
    """Return an explicit least-privilege default; unknown permissions fail closed."""
    return action in DEFAULT_ROLE_PERMISSIONS.get(role, {}).get(module_key, set())


def default_permission_matrix(role: str, modules: set[str], actions: set[str]) -> dict[str, bool]:
    return {
        f"{module}:{action}": default_role_permission(role, module, action)
        for module in modules
        for action in actions
    }


def require_module_permission(module_key: str, action: str, *fallback_roles: str):
    """Enforce school override, then ERP grant, then explicit least-privilege defaults.

    fallback_roles is retained for call-site compatibility only. Route fallback
    role lists must never grant access or override the role permission matrix.
    """
    def checker(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if user.role == "super_admin":
            return user

        grant = None
        if user.school_id is not None:
            grant = db.scalar(select(RolePermission).where(
                RolePermission.school_id == user.school_id,
                RolePermission.role == user.role,
                RolePermission.module_key == module_key,
                RolePermission.action == action,
            ))
        if grant is None:
            grant = db.scalar(select(RolePermission).where(
                RolePermission.school_id.is_(None),
                RolePermission.role == user.role,
                RolePermission.module_key == module_key,
                RolePermission.action == action,
            ))

        if grant is not None:
            if grant.enabled:
                return user
            raise HTTPException(status_code=403, detail=f"Permission denied: {module_key} / {action}")

        if default_role_permission(user.role, module_key, action):
            return user
        raise HTTPException(status_code=403, detail=f"Permission denied: {module_key} / {action}")

    return checker
