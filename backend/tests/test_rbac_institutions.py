import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app import models
from app.rbac_catalog import seed_rbac_catalog
from app.rbac_templates import create_role_template, create_template_version, publish_template_version
from app.rbac_institutions import (
    assign_institution_role,
    create_institution_role,
    set_role_assignment_active,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        school = models.School(name="North School", code="NORTH", institution_type="school")
        other_school = models.School(name="South School", code="SOUTH", institution_type="school")
        session.add_all([school, other_school])
        session.flush()
        admin = models.User(
            name="School Admin", email="admin@example.test", password_hash="x",
            role="admin", school_id=school.id,
        )
        user = models.User(
            name="Teacher", email="teacher@example.test", password_hash="x",
            role="teacher", school_id=school.id,
        )
        second_user = models.User(
            name="Accountant", email="accountant@example.test", password_hash="x",
            role="finance", school_id=school.id,
        )
        other_user = models.User(
            name="Other Teacher", email="other@example.test", password_hash="x",
            role="teacher", school_id=other_school.id,
        )
        platform_user = models.User(
            name="Platform Admin", email="platform@example.test", password_hash="x",
            role="super_admin",
        )
        session.add_all([admin, user, second_user, other_user, platform_user])
        session.flush()
        seed_rbac_catalog(session)
        template = create_role_template(
            session, template_key="school_staff", name="School Staff",
            description="School staff template", category="staff",
            actor_user_id=admin.id,
        )
        version = create_template_version(
            session, template_id=template.id, institution_types=["school"],
            permissions=[
                {"module_key": "attendance", "actions": ["View", "Edit"], "scope": "class_section"},
                {"module_key": "homework", "actions": ["View"], "scope": "class_section"},
            ],
            change_summary="Initial policy", actor_user_id=admin.id,
        )
        publish_template_version(session, version_id=version.id, actor_user_id=admin.id)
        session.commit()
        yield session, school, other_school, admin, user, second_user, other_user, platform_user, version
    engine.dispose()


def _create_role(db, school, admin, version, key="attendance_lead", actions=None):
    return create_institution_role(
        db,
        school_id=school.id,
        role_key=key,
        name="Attendance Lead",
        description="Local attendance coordinator",
        template_version_id=version.id,
        permissions=actions or [
            {"module_key": "attendance", "action_key": "View", "scope": "class_section"},
            {"module_key": "attendance", "action_key": "Edit", "scope": "class_section"},
        ],
        actor_user_id=admin.id,
    )


def test_create_institution_role_stays_inside_published_template_ceiling(db):
    session, school, _, admin, *_rest, version = db
    role = _create_role(session, school, admin, version)
    permissions = session.scalars(
        select(models.InstitutionRolePermission).where(
            models.InstitutionRolePermission.role_id == role.id
        )
    ).all()
    assert role.school_id == school.id
    assert role.source_template_version_id == version.id
    assert {(p.module_key, p.action_key, p.scope) for p in permissions} == {
        ("attendance", "View", "class_section"),
        ("attendance", "Edit", "class_section"),
    }
    assert session.scalar(select(models.AuditLog).where(
        models.AuditLog.event_type == "rbac.institution_role.created"
    )) is not None


def test_role_creation_rejects_permission_or_scope_outside_template(db):
    session, school, _, admin, *_rest, version = db
    with pytest.raises(ValueError, match="exceeds the adopted template"):
        _create_role(session, school, admin, version, actions=[
            {"module_key": "fees", "action_key": "View", "scope": "institution"},
        ])
    with pytest.raises(ValueError, match="Scope"):
        _create_role(session, school, admin, version, actions=[
            {"module_key": "attendance", "action_key": "View", "scope": "institution"},
        ])


def test_role_creation_requires_same_school_admin_and_applicable_published_template(db):
    session, school, other_school, admin, user, *_rest, version = db
    with pytest.raises(ValueError, match="administrator"):
        create_institution_role(
            session, school_id=school.id, role_key="bad", name="Bad",
            template_version_id=version.id, permissions=[], actor_user_id=user.id,
        )
    with pytest.raises(ValueError, match="administrator"):
        create_institution_role(
            session, school_id=other_school.id, role_key="bad", name="Bad",
            template_version_id=version.id, permissions=[], actor_user_id=admin.id,
        )


def test_multiple_roles_can_be_assigned_and_revoked_without_changing_legacy_role(db):
    session, school, _, admin, user, _, _, _, version = db
    first = _create_role(session, school, admin, version, key="attendance_lead")
    second = _create_role(session, school, admin, version, key="homework_viewer", actions=[
        {"module_key": "homework", "action_key": "View", "scope": "class_section"},
    ])
    one = assign_institution_role(
        session, school_id=school.id, user_id=user.id, role_id=first.id,
        actor_user_id=admin.id,
    )
    two = assign_institution_role(
        session, school_id=school.id, user_id=user.id, role_id=second.id,
        actor_user_id=admin.id,
    )
    assert one.id != two.id
    assert user.role == "teacher"
    assert len(session.scalars(select(models.UserRoleAssignment).where(
        models.UserRoleAssignment.user_id == user.id,
        models.UserRoleAssignment.is_active.is_(True),
    )).all()) == 2

    set_role_assignment_active(
        session, school_id=school.id, assignment_id=one.id,
        is_active=False, actor_user_id=admin.id,
    )
    assert not one.is_active
    with pytest.raises(ValueError, match="already has"):
        assign_institution_role(
            session, school_id=school.id, user_id=user.id, role_id=second.id,
            actor_user_id=admin.id,
        )
    session.commit()
    assert session.scalar(select(models.AuditLog).where(
        models.AuditLog.event_type == "rbac.role_assignment.revoked"
    )) is not None


def test_assignment_rejects_cross_tenant_users_roles_and_platform_accounts(db):
    session, school, _, admin, _, _, other_user, platform_user, version = db
    role = _create_role(session, school, admin, version)
    with pytest.raises(ValueError, match="user from this institution"):
        assign_institution_role(
            session, school_id=school.id, user_id=other_user.id,
            role_id=role.id, actor_user_id=admin.id,
        )
    with pytest.raises(ValueError, match="Platform administrators"):
        assign_institution_role(
            session, school_id=school.id, user_id=platform_user.id,
            role_id=role.id, actor_user_id=admin.id,
        )
    with pytest.raises(ValueError, match="not found"):
        assign_institution_role(
            session, school_id=school.id, user_id=admin.id,
            role_id=999999, actor_user_id=admin.id,
        )


def test_assignment_date_window_and_reactivation(db):
    session, school, _, admin, user, *_rest, version = db
    role = _create_role(session, school, admin, version)
    start = datetime.utcnow() + timedelta(days=1)
    with pytest.raises(ValueError, match="after its start"):
        assign_institution_role(
            session, school_id=school.id, user_id=user.id, role_id=role.id,
            actor_user_id=admin.id, starts_at=start, ends_at=start,
        )
    assignment = assign_institution_role(
        session, school_id=school.id, user_id=user.id, role_id=role.id,
        actor_user_id=admin.id,
    )
    set_role_assignment_active(
        session, school_id=school.id, assignment_id=assignment.id,
        is_active=False, actor_user_id=admin.id,
    )
    reactivated = assign_institution_role(
        session, school_id=school.id, user_id=user.id, role_id=role.id,
        actor_user_id=admin.id,
    )
    assert reactivated.id == assignment.id
    assert reactivated.is_active
