"""Developer-governed role-template persistence and lifecycle helpers.

This layer deliberately does not participate in request authorization yet.
Published versions are immutable through these service functions; later PRs
will expose audited Developer APIs and institution adoption workflows.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .rbac_catalog import seed_rbac_catalog

ALLOWED_SCOPES = {
    "own", "assigned", "class_section", "department",
    "institution", "selected_records", "parent_student_relationship",
}


def _validate_template_policy(
    db: Session,
    institution_types: list[str],
    permissions: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    if not isinstance(institution_types, list) or not institution_types:
        raise ValueError("At least one institution type is required")
    if len(set(institution_types)) != len(institution_types):
        raise ValueError("Institution types must not contain duplicates")

    active_types = set(db.scalars(
        select(models.RbacInstitutionType.key).where(models.RbacInstitutionType.is_active.is_(True))
    ).all())
    unknown_types = set(institution_types) - active_types
    if unknown_types:
        raise ValueError(f"Unsupported institution types: {', '.join(sorted(unknown_types))}")

    if not isinstance(permissions, list):
        raise ValueError("Permissions must be a list")
    modules = {
        item.key: item for item in db.scalars(
            select(models.RbacModule).where(models.RbacModule.is_active.is_(True))
        ).all()
    }
    allowed_pairs = set(db.execute(
        select(models.RbacModuleAction.module_key, models.RbacModuleAction.action_key)
        .where(models.RbacModuleAction.is_active.is_(True))
    ).all())
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for entry in permissions:
        if not isinstance(entry, dict):
            raise ValueError("Each permission entry must be an object")
        module_key = str(entry.get("module_key", "")).strip()
        actions = entry.get("actions")
        scope = str(entry.get("scope", "institution")).strip()
        module = modules.get(module_key)
        if module is None:
            raise ValueError(f"Unknown or inactive module: {module_key}")
        if module.is_platform_only:
            raise ValueError(f"Platform-only module cannot be included in a tenant template: {module_key}")
        if not set(institution_types).issubset(set(module.institution_types or [])):
            raise ValueError(f"Module {module_key} is not enabled for every selected institution type")
        if scope not in ALLOWED_SCOPES:
            raise ValueError(f"Unsupported data scope: {scope}")
        if not isinstance(actions, list) or not actions:
            raise ValueError(f"At least one action is required for module {module_key}")
        if len(set(actions)) != len(actions):
            raise ValueError(f"Duplicate actions for module {module_key}")
        for action in actions:
            if (module_key, action) not in allowed_pairs:
                raise ValueError(f"Action {action} is not allowed for module {module_key}")
            identity = (module_key, action)
            if identity in seen:
                raise ValueError(f"Duplicate permission: {module_key}:{action}")
            seen.add(identity)
        normalized.append({
            "module_key": module_key,
            "actions": sorted(actions),
            "scope": scope,
        })

    normalized.sort(key=lambda item: item["module_key"])
    return sorted(institution_types), normalized


def create_role_template(
    db: Session,
    *,
    template_key: str,
    name: str,
    description: str,
    category: str,
    actor_user_id: int,
) -> models.RbacRoleTemplate:
    key = template_key.strip().lower()
    label = name.strip()
    if not key or len(key) > 80 or not label or len(label) > 120:
        raise ValueError("A valid template key and name are required")
    if db.scalar(select(models.RbacRoleTemplate.id).where(models.RbacRoleTemplate.template_key == key)):
        raise ValueError("Template key already exists")
    template = models.RbacRoleTemplate(
        template_key=key,
        name=label,
        description=description.strip(),
        category=(category.strip() or "general")[:60],
        created_by=actor_user_id,
    )
    db.add(template)
    db.flush()
    return template


def create_template_version(
    db: Session,
    *,
    template_id: int,
    institution_types: list[str],
    permissions: list[dict[str, Any]],
    change_summary: str,
    actor_user_id: int,
) -> models.RbacRoleTemplateVersion:
    template = db.get(models.RbacRoleTemplate, template_id)
    if template is None or not template.is_active:
        raise ValueError("Active role template not found")
    seed_rbac_catalog(db)
    normalized_types, normalized_permissions = _validate_template_policy(
        db, institution_types, permissions
    )
    latest = db.scalar(
        select(func.max(models.RbacRoleTemplateVersion.version_number))
        .where(models.RbacRoleTemplateVersion.template_id == template_id)
    ) or 0
    version = models.RbacRoleTemplateVersion(
        template_id=template_id,
        version_number=latest + 1,
        status="draft",
        institution_types=normalized_types,
        permissions=normalized_permissions,
        change_summary=change_summary.strip(),
        created_by=actor_user_id,
    )
    db.add(version)
    db.flush()
    return version


def replace_draft_policy(
    db: Session,
    *,
    version_id: int,
    institution_types: list[str],
    permissions: list[dict[str, Any]],
    change_summary: str,
) -> models.RbacRoleTemplateVersion:
    version = db.get(models.RbacRoleTemplateVersion, version_id)
    if version is None:
        raise ValueError("Template version not found")
    if version.status != "draft" or version.published_at is not None:
        raise ValueError("Published or retired template versions are immutable")
    seed_rbac_catalog(db)
    normalized_types, normalized_permissions = _validate_template_policy(
        db, institution_types, permissions
    )
    version.institution_types = normalized_types
    version.permissions = normalized_permissions
    version.change_summary = change_summary.strip()
    return version


def publish_template_version(
    db: Session,
    *,
    version_id: int,
    actor_user_id: int,
) -> models.RbacRoleTemplateVersion:
    version = db.get(models.RbacRoleTemplateVersion, version_id)
    if version is None:
        raise ValueError("Template version not found")
    if version.status != "draft" or version.published_at is not None:
        raise ValueError("Only a draft template version can be published")
    # Revalidate at publication time so stale drafts cannot publish against
    # a module/action combination that has since been disabled.
    seed_rbac_catalog(db)
    types, permissions = _validate_template_policy(
        db, version.institution_types, version.permissions
    )
    version.institution_types = types
    version.permissions = permissions
    version.status = "published"
    version.published_by = actor_user_id
    version.published_at = datetime.utcnow()
    return version


def retire_template_version(
    db: Session,
    *,
    version_id: int,
    actor_user_id: int,
) -> models.RbacRoleTemplateVersion:
    """Retire a published version without rewriting its immutable policy."""
    version = db.get(models.RbacRoleTemplateVersion, version_id)
    if version is None:
        raise ValueError("Template version not found")
    if version.status != "published":
        raise ValueError("Only a published template version can be retired")
    version.status = "retired"
    return version


def set_role_template_active(
    db: Session,
    *,
    template_id: int,
    is_active: bool,
) -> models.RbacRoleTemplate:
    """Pause or reactivate a template; existing adopted roles are not modified."""
    template = db.get(models.RbacRoleTemplate, template_id)
    if template is None:
        raise ValueError("Role template not found")
    template.is_active = is_active
    return template
