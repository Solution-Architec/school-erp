from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app import models
from app.rbac_catalog import seed_rbac_catalog
from app.rbac_templates import create_role_template, create_template_version, publish_template_version
from app.rbac_institutions import create_institution_role, assign_institution_role
from app.rbac_resolver import resolve_custom_role_decision, resolve_effective_permission, compare_permission_decisions


@pytest.fixture()
def resolver_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        school = models.School(name="Resolver School", code="RESOLVE")
        session.add(school)
        session.flush()
        admin = models.User(name="Admin", email="resolver-admin@example.test", password_hash="x", role="admin", school_id=school.id)
        teacher = models.User(name="Teacher", email="resolver-teacher@example.test", password_hash="x", role="teacher", school_id=school.id)
        session.add_all([admin, teacher])
        session.flush()
        seed_rbac_catalog(session)
        template = create_role_template(session, template_key="resolver_staff", name="Resolver Staff", description="", category="staff", actor_user_id=admin.id)
        version = create_template_version(
            session, template_id=template.id, institution_types=["school"],
            permissions=[
                {"module_key": "attendance", "actions": ["View", "Edit"], "scope": "class_section"},
                {"module_key": "homework", "actions": ["View"], "scope": "assigned"},
            ],
            change_summary="Resolver tests", actor_user_id=admin.id,
        )
        publish_template_version(session, version_id=version.id, actor_user_id=admin.id)
        session.commit()
        yield session, school, admin, teacher, version
    engine.dispose()


def _role(session, school, admin, version, key, permissions):
    return create_institution_role(
        session, school_id=school.id, role_key=key, name=key.title(),
        template_version_id=version.id, permissions=permissions, actor_user_id=admin.id,
    )


def test_multi_role_resolver_unions_all_active_role_allows(resolver_db):
    session, school, admin, teacher, version = resolver_db
    attendance = _role(session, school, admin, version, "attendance_viewer", [
        {"module_key": "attendance", "action_key": "View", "scope": "class_section"},
    ])
    homework = _role(session, school, admin, version, "homework_viewer", [
        {"module_key": "homework", "action_key": "View", "scope": "assigned"},
    ])
    first = assign_institution_role(session, school_id=school.id, user_id=teacher.id, role_id=attendance.id, actor_user_id=admin.id)
    second = assign_institution_role(session, school_id=school.id, user_id=teacher.id, role_id=homework.id, actor_user_id=admin.id)

    attendance_decision = resolve_custom_role_decision(session, teacher, "attendance", "View")
    homework_decision = resolve_custom_role_decision(session, teacher, "homework", "View")
    assert attendance_decision is not None and attendance_decision.allowed
    assert attendance_decision.role_ids == (attendance.id,)
    assert attendance_decision.assignment_ids == (first.id,)
    assert homework_decision is not None and homework_decision.allowed
    assert homework_decision.scopes == ("assigned",)
    assert homework_decision.assignment_ids == (second.id,)


def test_explicit_deny_from_any_active_role_overrides_another_role_allow(resolver_db):
    session, school, admin, teacher, version = resolver_db
    allowed_role = _role(session, school, admin, version, "attendance_allow", [
        {"module_key": "attendance", "action_key": "View", "scope": "class_section"},
    ])
    denied_role = _role(session, school, admin, version, "attendance_deny", [])
    assign_institution_role(session, school_id=school.id, user_id=teacher.id, role_id=allowed_role.id, actor_user_id=admin.id)
    assign_institution_role(session, school_id=school.id, user_id=teacher.id, role_id=denied_role.id, actor_user_id=admin.id)
    session.add(models.InstitutionRolePermission(
        school_id=school.id, role_id=denied_role.id, module_key="attendance",
        action_key="View", scope="class_section", enabled=False,
    ))
    session.flush()

    decision = resolve_custom_role_decision(session, teacher, "attendance", "View")
    assert decision is not None and decision.allowed is False
    assert decision.explicit_deny is True
    assert decision.source == "institution_role_explicit_deny"


def test_inactive_expired_and_future_assignments_do_not_grant(resolver_db):
    session, school, admin, teacher, version = resolver_db
    role = _role(session, school, admin, version, "future_attendance", [
        {"module_key": "attendance", "action_key": "View", "scope": "class_section"},
    ])
    future = assign_institution_role(
        session, school_id=school.id, user_id=teacher.id, role_id=role.id,
        actor_user_id=admin.id, starts_at=datetime.utcnow() + timedelta(days=1),
    )
    now = datetime.utcnow()
    assert resolve_custom_role_decision(session, teacher, "attendance", "View", now=now) is None
    future.starts_at = now - timedelta(days=2)
    future.ends_at = now - timedelta(days=1)
    session.flush()
    assert resolve_custom_role_decision(session, teacher, "attendance", "View", now=now) is None
    future.ends_at = None
    future.is_active = False
    session.flush()
    assert resolve_custom_role_decision(session, teacher, "attendance", "View", now=now) is None


def test_effective_resolver_uses_legacy_when_no_custom_role_decides(resolver_db):
    session, school, admin, teacher, version = resolver_db
    decision = resolve_effective_permission(session, teacher, "homework", "View")
    assert decision.allowed is True
    assert decision.source == "legacy_default_matrix"


def test_shadow_comparison_reports_parity_without_changing_authorization(resolver_db):
    session, school, admin, teacher, version = resolver_db
    result = compare_permission_decisions(session, teacher, "homework", "View")
    assert result["legacy_allowed"] is True
    assert result["proposed_allowed"] is True
    assert result["changed"] is False
