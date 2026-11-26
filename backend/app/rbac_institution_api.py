"""Institution-admin APIs for local custom roles and multiple role assignments."""
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .rbac_institutions import (
    assign_institution_role,
    create_institution_role,
    set_role_assignment_active,
)
from .security import require_roles

router = APIRouter(prefix="/api/institution/rbac", tags=["institution-rbac"])


class RoleCreateIn(BaseModel):
    role_key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    template_version_id: int
    permissions: list[dict[str, Any]] = Field(default_factory=list, max_length=300)


class AssignmentCreateIn(BaseModel):
    user_id: int
    role_id: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AssignmentActiveIn(BaseModel):
    is_active: bool


def _school_id(user: models.User) -> int:
    if not user.school_id:
        raise HTTPException(status_code=403, detail="Your account is not assigned to an institution")
    return int(user.school_id)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="The requested role or assignment conflicts with an existing record")


def _role_out(db: Session, role: models.InstitutionRole) -> dict[str, Any]:
    version = db.get(models.RbacRoleTemplateVersion, role.source_template_version_id)
    template = db.get(models.RbacRoleTemplate, version.template_id) if version else None
    permissions = db.scalars(
        select(models.InstitutionRolePermission)
        .where(
            models.InstitutionRolePermission.school_id == role.school_id,
            models.InstitutionRolePermission.role_id == role.id,
        )
        .order_by(models.InstitutionRolePermission.module_key, models.InstitutionRolePermission.action_key)
    ).all()
    from sqlalchemy import func
    assignment_count = db.scalar(select(func.count(models.UserRoleAssignment.id)).where(
        models.UserRoleAssignment.school_id == role.school_id,
        models.UserRoleAssignment.role_id == role.id,
        models.UserRoleAssignment.is_active.is_(True),
    )) or 0
    return {
        "id": role.id, "school_id": role.school_id, "role_key": role.role_key,
        "name": role.name, "description": role.description, "is_active": role.is_active,
        "source_template_version_id": role.source_template_version_id,
        "source_template_name": template.name if template else "Developer template",
        "source_template_key": template.template_key if template else "",
        "source_version_number": version.version_number if version else None,
        "permissions": [{
            "module_key": item.module_key, "action_key": item.action_key,
            "scope": item.scope, "enabled": item.enabled,
        } for item in permissions],
        "active_assignment_count": assignment_count,
        "created_at": role.created_at, "updated_at": role.updated_at,
    }


def _assignment_out(assignment: models.UserRoleAssignment, user: models.User, role: models.InstitutionRole) -> dict[str, Any]:
    return {
        "id": assignment.id, "school_id": assignment.school_id,
        "user_id": user.id, "user_name": user.name, "user_email": user.email,
        "legacy_role": user.role, "role_id": role.id, "role_name": role.name,
        "role_key": role.role_key, "is_active": assignment.is_active,
        "starts_at": assignment.starts_at, "ends_at": assignment.ends_at,
        "assigned_by": assignment.assigned_by, "created_at": assignment.created_at,
    }


@router.get("/context")
def institution_rbac_context(
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    school = db.get(models.School, school_id)
    if school is None or not school.is_active:
        raise HTTPException(status_code=404, detail="Active institution not found")
    return {"school_id": school.id, "school_name": school.name, "institution_type": school.institution_type}


@router.get("/templates")
def list_adoptable_templates(
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    school = db.get(models.School, school_id)
    if school is None or not school.is_active:
        raise HTTPException(status_code=404, detail="Active institution not found")
    rows = db.execute(
        select(models.RbacRoleTemplate, models.RbacRoleTemplateVersion)
        .join(models.RbacRoleTemplateVersion, models.RbacRoleTemplateVersion.template_id == models.RbacRoleTemplate.id)
        .where(
            models.RbacRoleTemplate.is_active.is_(True),
            models.RbacRoleTemplateVersion.status == "published",
        )
        .order_by(models.RbacRoleTemplate.name, models.RbacRoleTemplateVersion.version_number.desc())
    ).all()
    result = []
    seen: set[int] = set()
    for template, version in rows:
        if version.id in seen or school.institution_type not in (version.institution_types or []):
            continue
        seen.add(version.id)
        result.append({
            "template_id": template.id, "template_key": template.template_key,
            "template_name": template.name, "description": template.description,
            "category": template.category, "version_id": version.id,
            "version_number": version.version_number,
            "institution_types": version.institution_types or [],
            "permissions": version.permissions or [],
            "change_summary": version.change_summary,
        })
    return result


@router.get("/roles")
def list_institution_roles(
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    roles = db.scalars(
        select(models.InstitutionRole)
        .where(models.InstitutionRole.school_id == school_id)
        .order_by(models.InstitutionRole.name)
    ).all()
    return [_role_out(db, role) for role in roles]


@router.post("/roles", status_code=201)
def create_institution_role_api(
    payload: RoleCreateIn,
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    try:
        role = create_institution_role(
            db, school_id=school_id, role_key=payload.role_key, name=payload.name,
            description=payload.description, template_version_id=payload.template_version_id,
            permissions=payload.permissions, actor_user_id=user.id,
        )
        _commit(db)
        db.refresh(role)
        return _role_out(db, role)
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        status = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status, detail=message)


@router.get("/users")
def list_assignable_users(
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    users = db.scalars(
        select(models.User)
        .where(
            models.User.school_id == school_id,
            models.User.is_active.is_(True),
            models.User.role.notin_(["super_admin", "parent"]),
        )
        .order_by(models.User.name)
    ).all()
    return [{
        "id": item.id, "name": item.name, "email": item.email,
        "role": item.role, "position": item.position,
    } for item in users]


@router.get("/assignments")
def list_role_assignments(
    user_id: int | None = None,
    role_id: int | None = None,
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    stmt = (
        select(models.UserRoleAssignment, models.User, models.InstitutionRole)
        .join(models.User, models.User.id == models.UserRoleAssignment.user_id)
        .join(models.InstitutionRole, models.InstitutionRole.id == models.UserRoleAssignment.role_id)
        .where(
            models.UserRoleAssignment.school_id == school_id,
            models.UserRoleAssignment.is_active.is_(True),
        )
    )
    if user_id is not None:
        stmt = stmt.where(models.UserRoleAssignment.user_id == user_id)
    if role_id is not None:
        stmt = stmt.where(models.UserRoleAssignment.role_id == role_id)
    rows = db.execute(stmt.order_by(models.User.name, models.InstitutionRole.name)).all()
    return [_assignment_out(assignment, assigned_user, role) for assignment, assigned_user, role in rows]


@router.post("/assignments", status_code=201)
def create_role_assignment_api(
    payload: AssignmentCreateIn,
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    target = db.get(models.User, payload.user_id)
    if target is None or target.role in {"super_admin", "parent"}:
        raise HTTPException(status_code=404, detail="Eligible staff account not found in this institution")
    try:
        assignment = assign_institution_role(
            db, school_id=school_id, user_id=payload.user_id, role_id=payload.role_id,
            actor_user_id=user.id, starts_at=payload.starts_at, ends_at=payload.ends_at,
        )
        _commit(db)
        db.refresh(assignment)
        role = db.get(models.InstitutionRole, assignment.role_id)
        assigned_user = db.get(models.User, assignment.user_id)
        return _assignment_out(assignment, assigned_user, role)
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        status = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status, detail=message)


@router.patch("/assignments/{assignment_id}")
def update_role_assignment_api(
    assignment_id: int,
    payload: AssignmentActiveIn,
    user: models.User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(user)
    try:
        assignment = set_role_assignment_active(
            db, school_id=school_id, assignment_id=assignment_id,
            is_active=payload.is_active, actor_user_id=user.id,
        )
        _commit(db)
        assigned_user = db.get(models.User, assignment.user_id)
        role = db.get(models.InstitutionRole, assignment.role_id)
        return _assignment_out(assignment, assigned_user, role)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
