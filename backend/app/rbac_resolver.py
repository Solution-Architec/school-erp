"""Deterministic multi-role permission resolution (shadow-mode foundation).

This module is intentionally not wired into request authorization in this PR.
It evaluates current institution role assignments on every call so revocation
and assignment expiry take effect immediately. Legacy authorization remains
the live source of truth until route-by-route parity is verified.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from . import models


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    source: str
    scopes: tuple[str, ...] = ()
    role_ids: tuple[int, ...] = ()
    assignment_ids: tuple[int, ...] = ()
    explicit_deny: bool = False


def _as_utc_naive(value: datetime) -> datetime:
    """The current schema stores naive UTC datetimes; normalize aware inputs."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def resolve_custom_role_decision(
    db: Session,
    user: models.User,
    module_key: str,
    action_key: str,
    *,
    now: datetime | None = None,
) -> PermissionDecision | None:
    """Resolve a module/action across all currently active institution roles.

    A stored enabled=False row is an explicit deny; enabled=True is an allow;
    absence of a row is inherit. Any explicit deny wins over every role allow.
    A role with no matching row does not decide this permission.
    """
    school_id = getattr(user, "school_id", None)
    user_id = getattr(user, "id", None)
    if (
        not user_id
        or not school_id
        or not getattr(user, "is_active", False)
        or getattr(user, "role", None) == "super_admin"
    ):
        return None

    instant = _as_utc_naive(now or datetime.now(timezone.utc))
    permission_join = and_(
        models.InstitutionRolePermission.role_id == models.InstitutionRole.id,
        models.InstitutionRolePermission.school_id == school_id,
        models.InstitutionRolePermission.module_key == module_key,
        models.InstitutionRolePermission.action_key == action_key,
    )
    rows = db.execute(
        select(
            models.UserRoleAssignment,
            models.InstitutionRole,
            models.InstitutionRolePermission,
        )
        .join(
            models.InstitutionRole,
            and_(
                models.InstitutionRole.id == models.UserRoleAssignment.role_id,
                models.InstitutionRole.school_id == models.UserRoleAssignment.school_id,
            ),
        )
        .outerjoin(models.InstitutionRolePermission, permission_join)
        .where(
            models.UserRoleAssignment.user_id == user_id,
            models.UserRoleAssignment.school_id == school_id,
            models.UserRoleAssignment.is_active.is_(True),
            models.UserRoleAssignment.starts_at <= instant,
            or_(
                models.UserRoleAssignment.ends_at.is_(None),
                models.UserRoleAssignment.ends_at > instant,
            ),
            models.InstitutionRole.is_active.is_(True),
        )
    ).all()

    allows: list[tuple[int, int, str]] = []
    denies: list[tuple[int, int]] = []
    for assignment, role, permission in rows:
        if permission is None:
            continue
        if permission.enabled:
            allows.append((role.id, assignment.id, permission.scope))
        else:
            denies.append((role.id, assignment.id))

    if denies:
        return PermissionDecision(
            allowed=False,
            source="institution_role_explicit_deny",
            role_ids=tuple(sorted({role_id for role_id, _ in denies})),
            assignment_ids=tuple(sorted({assignment_id for _, assignment_id in denies})),
            explicit_deny=True,
        )
    if allows:
        return PermissionDecision(
            allowed=True,
            source="institution_role",
            scopes=tuple(sorted({scope for _, _, scope in allows})),
            role_ids=tuple(sorted({role_id for role_id, _, _ in allows})),
            assignment_ids=tuple(sorted({assignment_id for _, assignment_id, _ in allows})),
        )
    return None


def legacy_permission_decision(
    db: Session,
    user: models.User,
    module_key: str,
    action_key: str,
    *,
    fallback_roles: Iterable[str] = (),
) -> PermissionDecision:
    """Mirror the existing require_module_permission grant/default/fallback order."""
    if getattr(user, "role", None) == "super_admin":
        return PermissionDecision(True, "platform_super_admin")

    school_grant = None
    if getattr(user, "school_id", None) is not None:
        school_grant = db.scalar(
            select(models.RolePermission).where(
                models.RolePermission.role == user.role,
                models.RolePermission.school_id == user.school_id,
                models.RolePermission.module_key == module_key,
                models.RolePermission.action == action_key,
            )
        )
    grant = school_grant or db.scalar(
        select(models.RolePermission).where(
            models.RolePermission.role == user.role,
            models.RolePermission.school_id.is_(None),
            models.RolePermission.module_key == module_key,
            models.RolePermission.action == action_key,
        )
    )
    if grant is not None:
        return PermissionDecision(bool(grant.enabled), "legacy_role_permission")

    try:
        from .main import RBAC_MODULES, _default_permission_matrix

        if module_key in RBAC_MODULES:
            allowed = bool(
                _default_permission_matrix(user.role).get(
                    f"{module_key}:{action_key}", False
                )
            )
            return PermissionDecision(allowed, "legacy_default_matrix")
    except ImportError:
        # Keep the same conservative behavior as the legacy checker if the
        # application module is unavailable in a minimal test environment.
        pass

    if module_key in {"library-books", "library-loans"}:
        library_roles = {"admin", "principal", "vice_principal", "user", "librarian"}
        if user.role not in library_roles:
            return PermissionDecision(False, "legacy_library_fallback")
        if action_key == "Delete" and user.role not in {"admin", "user"}:
            return PermissionDecision(False, "legacy_library_fallback")
        return PermissionDecision(True, "legacy_library_fallback")

    return PermissionDecision(
        user.role in set(fallback_roles),
        "legacy_route_fallback",
    )


def resolve_effective_permission(
    db: Session,
    user: models.User,
    module_key: str,
    action_key: str,
    *,
    fallback_roles: Iterable[str] = (),
    now: datetime | None = None,
) -> PermissionDecision:
    """Return proposed multi-role decision, falling back to legacy if undecided."""
    custom = resolve_custom_role_decision(
        db, user, module_key, action_key, now=now
    )
    if custom is not None:
        return custom
    return legacy_permission_decision(
        db, user, module_key, action_key, fallback_roles=fallback_roles
    )


def compare_permission_decisions(
    db: Session,
    user: models.User,
    module_key: str,
    action_key: str,
    *,
    fallback_roles: Iterable[str] = (),
    now: datetime | None = None,
) -> dict[str, object]:
    """Return a side-effect-free parity record for future shadow-mode telemetry."""
    legacy = legacy_permission_decision(
        db, user, module_key, action_key, fallback_roles=fallback_roles
    )
    proposed = resolve_effective_permission(
        db, user, module_key, action_key,
        fallback_roles=fallback_roles, now=now,
    )
    return {
        "legacy_allowed": legacy.allowed,
        "proposed_allowed": proposed.allowed,
        "changed": legacy.allowed != proposed.allowed,
        "legacy_source": legacy.source,
        "proposed_source": proposed.source,
        "module_key": module_key,
        "action_key": action_key,
    }
