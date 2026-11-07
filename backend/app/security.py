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
    """Authorize Developer-only routes strictly and unify all school-user roles.

    Legacy school roles remain valid for existing accounts, but they all receive
    the same operational permissions. Parent accounts are deliberately excluded
    from operational access and use only their linked-student endpoints.
    """
    allows_standard_users = bool(STANDARD_USER_ROLES.intersection(roles))

    def checker(user: User = Depends(current_user)) -> User:
        if user.role in roles:
            return user
        if allows_standard_users and user.role != "parent":
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker


def require_module_permission(module_key: str, action: str, *fallback_roles: str):
    """Use saved role grants when configured; otherwise preserve legacy route policy."""
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
        if grant is not None:
            if grant.enabled:
                return user
            raise HTTPException(status_code=403, detail=f"Permission denied: {module_key} / {action}")
        if module_key in {"library-books", "library-loans"} and user.role not in {"admin", "principal", "vice_principal", "user", "librarian"}:
            raise HTTPException(status_code=403, detail="Library access is restricted to school leadership and librarians")
        allows_standard_users = bool(STANDARD_USER_ROLES.intersection(fallback_roles))
        if user.role in fallback_roles or (allows_standard_users and user.role not in ("parent", "super_admin")):
            return user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return checker
