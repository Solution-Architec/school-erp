import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import get_db
from .models import User, RolePermission, School
from .security_config import load_jwt_secret

# Fail closed during application import/startup: there is no development fallback.
JWT_SECRET_KEY = load_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(user: User, workspace_school_id: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role, "iat": now,
               "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    if workspace_school_id is not None:
        payload["workspace_school_id"] = int(workspace_school_id)
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
    # Enforce tenant suspension on every authenticated request, including
    # already-issued access tokens, not only on the next login attempt.
    user_school_id = getattr(user, "school_id", None)
    if user.role != "super_admin" and user_school_id is not None:
        tenant_school = db.get(School, user_school_id)
        if not tenant_school or not tenant_school.is_active or tenant_school.approval_status == "archived":
            raise HTTPException(status_code=403, detail="This institution is paused or archived. Contact EduNexus support.")
    workspace_school_id = payload.get("workspace_school_id")
    if workspace_school_id is not None:
        if user.role != "super_admin":
            raise HTTPException(status_code=403, detail="Only the platform owner can enter a client workspace")
        try:
            workspace_school_id = int(workspace_school_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Invalid client workspace token")
        school = db.get(School, workspace_school_id)
        if not school or not school.is_active:
            raise HTTPException(status_code=403, detail="Client institution is unavailable")
        # A short-lived, signed workspace token presents the platform owner as a
        # tenant admin for exactly one school. Platform-only routes reject this
        # wrapper because its effective role is admin, not super_admin.
        return SimpleNamespace(
            id=user.id, name=user.name, email=user.email, role="admin",
            school_id=school.id, is_active=user.is_active,
            platform_owner_id=user.id, is_platform_workspace=True,
            platform_school_name=school.name,
        )
    return user

def require_roles(*roles: str):
    """Authorize only the explicitly listed roles; never broaden an admin grant."""
    def checker(user: User = Depends(current_user)) -> User:
        if user.role in roles:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker


def require_module_permission(module_key: str, action: str, *fallback_roles: str):
    """Use saved role grants when configured; otherwise preserve legacy route policy."""
    def checker(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if getattr(user, "is_platform_workspace", False):
            return user
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
        if grant is not None:
            if grant.enabled:
                return user
            raise HTTPException(status_code=403, detail=f"Permission denied: {module_key} / {action}")
        if module_key in {"library-books", "library-loans"}:
            library_roles = {"admin", "principal", "vice_principal", "user", "librarian"}
            if user.role not in library_roles:
                raise HTTPException(status_code=403, detail="Library access is restricted to school leadership and librarians")
            if action == "Delete" and user.role not in {"admin", "user"}:
                raise HTTPException(status_code=403, detail="Only school administrators can delete library records")
        if user.role in fallback_roles:
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker
