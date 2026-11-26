"""Developer-only APIs for governed RBAC role templates."""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .rbac_catalog import catalog_snapshot, seed_rbac_catalog
from .rbac_templates import (
    create_role_template,
    create_template_version,
    publish_template_version,
    replace_draft_policy,
    retire_template_version,
)
from .security import require_roles

router = APIRouter(prefix="/api/developer/rbac", tags=["developer-rbac"])


class TemplateCreateIn(BaseModel):
    template_key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="general", max_length=60)


class TemplateUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class VersionCreateIn(BaseModel):
    institution_types: list[str] = Field(min_length=1, max_length=20)
    permissions: list[dict[str, Any]] = Field(default_factory=list, max_length=300)
    change_summary: str = Field(min_length=1, max_length=2000)


class VersionUpdateIn(BaseModel):
    institution_types: list[str] = Field(min_length=1, max_length=20)
    permissions: list[dict[str, Any]] = Field(default_factory=list, max_length=300)
    change_summary: str = Field(min_length=1, max_length=2000)


def _audit(db: Session, actor: models.User, event: str, target_type: str,
           target_id: str, details: dict[str, Any]) -> None:
    db.add(models.AuditLog(
        actor_user_id=actor.id,
        event_type=event,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details, separators=(",", ":"), sort_keys=True),
    ))


def _version_out(version: models.RbacRoleTemplateVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "template_id": version.template_id,
        "version_number": version.version_number,
        "status": version.status,
        "institution_types": version.institution_types or [],
        "permissions": version.permissions or [],
        "change_summary": version.change_summary,
        "created_by": version.created_by,
        "published_by": version.published_by,
        "created_at": version.created_at,
        "published_at": version.published_at,
    }


def _template_out(template: models.RbacRoleTemplate, db: Session, *, include_versions: bool = True) -> dict[str, Any]:
    result = {
        "id": template.id,
        "template_key": template.template_key,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "is_active": template.is_active,
        "created_by": template.created_by,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }
    if include_versions:
        versions = db.scalars(
            select(models.RbacRoleTemplateVersion)
            .where(models.RbacRoleTemplateVersion.template_id == template.id)
            .order_by(models.RbacRoleTemplateVersion.version_number.desc())
        ).all()
        result["versions"] = [_version_out(item) for item in versions]
    return result


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="The requested template change conflicts with an existing record")


@router.get("/catalog")
def get_developer_rbac_catalog(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    seed_rbac_catalog(db)
    db.commit()
    return catalog_snapshot(db, include_platform=True)


@router.get("/templates")
def list_role_templates(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    query = select(models.RbacRoleTemplate).order_by(models.RbacRoleTemplate.name)
    if not include_inactive:
        query = query.where(models.RbacRoleTemplate.is_active.is_(True))
    templates = db.scalars(query).all()
    return [_template_out(item, db) for item in templates]


@router.post("/templates", status_code=201)
def create_role_template_api(
    payload: TemplateCreateIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    try:
        template = create_role_template(
            db, template_key=payload.template_key, name=payload.name,
            description=payload.description, category=payload.category,
            actor_user_id=user.id,
        )
        _audit(db, user, "rbac.template.created", "rbac_role_template", str(template.id),
               {"template_key": template.template_key, "name": template.name})
        _commit(db)
        db.refresh(template)
        return _template_out(template, db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/templates/{template_id}")
def get_role_template_api(
    template_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    template = db.get(models.RbacRoleTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Role template not found")
    return _template_out(template, db)


@router.patch("/templates/{template_id}")
def update_role_template_api(
    template_id: int,
    payload: TemplateUpdateIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    template = db.get(models.RbacRoleTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Role template not found")
    changes: dict[str, Any] = {}
    for field in ("name", "description", "category", "is_active"):
        value = getattr(payload, field)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if field in {"name", "category"} and not value:
                raise HTTPException(status_code=422, detail=f"{field} cannot be blank")
        old = getattr(template, field)
        if old != value:
            changes[field] = {"from": old, "to": value}
            setattr(template, field, value)
    if changes:
        _audit(db, user, "rbac.template.updated", "rbac_role_template", str(template.id),
               {"changes": changes})
        _commit(db)
        db.refresh(template)
    return _template_out(template, db)


@router.post("/templates/{template_id}/versions", status_code=201)
def create_role_template_version_api(
    template_id: int,
    payload: VersionCreateIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    try:
        version = create_template_version(
            db, template_id=template_id, institution_types=payload.institution_types,
            permissions=payload.permissions, change_summary=payload.change_summary,
            actor_user_id=user.id,
        )
        _audit(db, user, "rbac.template.version.created", "rbac_role_template_version",
               str(version.id), {"template_id": template_id, "version_number": version.version_number})
        _commit(db)
        db.refresh(version)
        return _version_out(version)
    except ValueError as exc:
        db.rollback()
        status = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=status, detail=str(exc))


@router.patch("/versions/{version_id}")
def update_role_template_version_api(
    version_id: int,
    payload: VersionUpdateIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    try:
        version = replace_draft_policy(
            db, version_id=version_id, institution_types=payload.institution_types,
            permissions=payload.permissions, change_summary=payload.change_summary,
        )
        _audit(db, user, "rbac.template.version.updated", "rbac_role_template_version",
               str(version.id), {"template_id": version.template_id, "version_number": version.version_number})
        _commit(db)
        db.refresh(version)
        return _version_out(version)
    except ValueError as exc:
        db.rollback()
        status = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=status, detail=str(exc))


@router.post("/versions/{version_id}/publish")
def publish_role_template_version_api(
    version_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    try:
        version = publish_template_version(db, version_id=version_id, actor_user_id=user.id)
        _audit(db, user, "rbac.template.version.published", "rbac_role_template_version",
               str(version.id), {"template_id": version.template_id, "version_number": version.version_number})
        _commit(db)
        db.refresh(version)
        return _version_out(version)
    except ValueError as exc:
        db.rollback()
        status = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=status, detail=str(exc))


@router.post("/versions/{version_id}/retire")
def retire_role_template_version_api(
    version_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("super_admin")),
):
    try:
        version = retire_template_version(db, version_id=version_id, actor_user_id=user.id)
        _audit(db, user, "rbac.template.version.retired", "rbac_role_template_version",
               str(version.id), {"template_id": version.template_id, "version_number": version.version_number})
        _commit(db)
        db.refresh(version)
        return _version_out(version)
    except ValueError as exc:
        db.rollback()
        status = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=status, detail=str(exc))
