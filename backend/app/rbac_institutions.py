"""Institution-local custom roles and multiple user-role assignments.

This persistence/service layer does not alter effective authorization. The
multi-role resolver and public APIs are delivered in later RBAC stages.
"""
import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


ALLOWED_SCOPES = {
    "own", "assigned", "class_section", "department",
    "institution", "selected_records", "parent_student_relationship",
}


def _school_admin(db: Session, *, school_id: int, actor_user_id: int) -> models.User:
    actor = db.get(models.User, actor_user_id)
    if (
        actor is None
        or not actor.is_active
        or actor.role != "admin"
        or actor.school_id != school_id
    ):
        raise ValueError("An active administrator from this institution is required")
    school = db.get(models.School, school_id)
    if school is None or not school.is_active:
        raise ValueError("Active institution not found")
    return actor


def _normalize_role_permissions(
    template_version: models.RbacRoleTemplateVersion,
    permissions: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if not isinstance(permissions, list):
        raise ValueError("Permissions must be a list")
    ceiling: dict[tuple[str, str], str] = {}
    for entry in template_version.permissions or []:
        for action in entry.get("actions", []):
            ceiling[(entry["module_key"], action)] = entry["scope"]

    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in permissions:
        if not isinstance(entry, dict):
            raise ValueError("Each role permission must be an object")
        module_key = str(entry.get("module_key", "")).strip()
        action_key = str(entry.get("action_key", "")).strip()
        scope = str(entry.get("scope", "")).strip()
        identity = (module_key, action_key)
        if identity in seen:
            raise ValueError(f"Duplicate role permission: {module_key}:{action_key}")
        if identity not in ceiling:
            raise ValueError(
                f"Permission exceeds the adopted template: {module_key}:{action_key}"
            )
        if scope not in ALLOWED_SCOPES or scope != ceiling[identity]:
            raise ValueError(
                f"Scope for {module_key}:{action_key} exceeds the template ceiling"
            )
        seen.add(identity)
        normalized.append({
            "module_key": module_key,
            "action_key": action_key,
            "scope": scope,
        })
    return sorted(normalized, key=lambda item: (item["module_key"], item["action_key"]))


def create_institution_role(
    db: Session,
    *,
    school_id: int,
    role_key: str,
    name: str,
    description: str = "",
    template_version_id: int,
    permissions: list[dict[str, Any]],
    actor_user_id: int,
) -> models.InstitutionRole:
    _school_admin(db, school_id=school_id, actor_user_id=actor_user_id)
    key = re.sub(r"[^a-z0-9_]+", "_", role_key.strip().lower()).strip("_")
    label = name.strip()
    if not key or len(key) > 80 or not label or len(label) > 120:
        raise ValueError("A valid role key and name are required")
    if db.scalar(select(models.InstitutionRole.id).where(
        models.InstitutionRole.school_id == school_id,
        models.InstitutionRole.role_key == key,
    )):
        raise ValueError("Role key already exists in this institution")

    version = db.get(models.RbacRoleTemplateVersion, template_version_id)
    if version is None or version.status != "published":
        raise ValueError("A published Developer template version is required")
    template = db.get(models.RbacRoleTemplate, version.template_id)
    if template is None or not template.is_active:
        raise ValueError("Active Developer template not found")
    school = db.get(models.School, school_id)
    if school.institution_type not in (version.institution_types or []):
        raise ValueError("Template is not applicable to this institution type")

    normalized = _normalize_role_permissions(version, permissions)
    role = models.InstitutionRole(
        school_id=school_id,
        role_key=key,
        name=label,
        description=description.strip(),
        source_template_version_id=version.id,
        created_by=actor_user_id,
        is_active=True,
    )
    db.add(role)
    db.flush()
    for item in normalized:
        db.add(models.InstitutionRolePermission(
            school_id=school_id,
            role_id=role.id,
            module_key=item["module_key"],
            action_key=item["action_key"],
            scope=item["scope"],
            enabled=True,
        ))
    db.add(models.AuditLog(
        actor_user_id=actor_user_id,
        event_type="rbac.institution_role.created",
        target_type="institution_role",
        target_id=str(role.id),
        details=json.dumps({
            "school_id": school_id,
            "role_key": key,
            "template_version_id": version.id,
            "permission_count": len(normalized),
        }, sort_keys=True, separators=(",", ":")),
    ))
    db.flush()
    return role


def assign_institution_role(
    db: Session,
    *,
    school_id: int,
    user_id: int,
    role_id: int,
    actor_user_id: int,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> models.UserRoleAssignment:
    _school_admin(db, school_id=school_id, actor_user_id=actor_user_id)
    user = db.get(models.User, user_id)
    role = db.get(models.InstitutionRole, role_id)
    if user is None or not user.is_active or user.school_id != school_id:
        raise ValueError("Active user from this institution not found")
    if user.role == "super_admin":
        raise ValueError("Platform administrators cannot receive institution roles")
    if role is None or role.school_id != school_id or not role.is_active:
        raise ValueError("Active role from this institution not found")

    start = starts_at or datetime.utcnow()
    if ends_at is not None and ends_at <= start:
        raise ValueError("Assignment end must be after its start")
    assignment = db.scalar(select(models.UserRoleAssignment).where(
        models.UserRoleAssignment.school_id == school_id,
        models.UserRoleAssignment.user_id == user_id,
        models.UserRoleAssignment.role_id == role_id,
    ))
    if assignment is None:
        assignment = models.UserRoleAssignment(
            school_id=school_id,
            user_id=user_id,
            role_id=role_id,
            assigned_by=actor_user_id,
            starts_at=start,
            ends_at=ends_at,
            is_active=True,
        )
        db.add(assignment)
        event = "rbac.role_assignment.created"
    else:
        if assignment.is_active:
            raise ValueError("User already has this active role assignment")
        assignment.is_active = True
        assignment.starts_at = start
        assignment.ends_at = ends_at
        assignment.assigned_by = actor_user_id
        event = "rbac.role_assignment.reactivated"

    db.add(models.AuditLog(
        actor_user_id=actor_user_id,
        event_type=event,
        target_type="user_role_assignment",
        target_id=str(assignment.id or "new"),
        details=json.dumps({
            "school_id": school_id, "user_id": user_id, "role_id": role_id,
        }, sort_keys=True, separators=(",", ":")),
    ))
    db.flush()
    return assignment


def set_role_assignment_active(
    db: Session,
    *,
    school_id: int,
    assignment_id: int,
    is_active: bool,
    actor_user_id: int,
) -> models.UserRoleAssignment:
    _school_admin(db, school_id=school_id, actor_user_id=actor_user_id)
    assignment = db.get(models.UserRoleAssignment, assignment_id)
    if assignment is None or assignment.school_id != school_id:
        raise ValueError("Role assignment not found in this institution")
    if assignment.is_active == is_active:
        return assignment
    assignment.is_active = is_active
    db.add(models.AuditLog(
        actor_user_id=actor_user_id,
        event_type="rbac.role_assignment.activated" if is_active else "rbac.role_assignment.revoked",
        target_type="user_role_assignment",
        target_id=str(assignment.id),
        details=json.dumps({
            "school_id": school_id,
            "user_id": assignment.user_id,
            "role_id": assignment.role_id,
        }, sort_keys=True, separators=(",", ":")),
    ))
    db.flush()
    return assignment
