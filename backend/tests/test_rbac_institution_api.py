from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import AuditLog, InstitutionRole, User, UserRoleAssignment
from backend.app.rbac_catalog import seed_rbac_catalog
from backend.app.rbac_templates import create_role_template, create_template_version, publish_template_version
from backend.app.security import current_user


def _client_for(user):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    school = user.school_id
    if school is None:
        school_obj = __import__("backend.app.models", fromlist=["School"]).School(
            name="North School", code="NORTH", institution_type="school"
        )
        session.add(school_obj)
        session.flush()
        user.school_id = school_obj.id
        school = school_obj.id
    session.add(user)
    session.flush()
    staff = User(name="Teacher", email="teacher@api.test", password_hash="x", role="teacher", school_id=school)
    session.add(staff)
    seed_rbac_catalog(session)
    template = create_role_template(
        session, template_key="api_staff_template", name="API Staff Template",
        description="Institution API test template", category="staff", actor_user_id=user.id,
    )
    version = create_template_version(
        session, template_id=template.id, institution_types=["school"],
        permissions=[
            {"module_key": "attendance", "actions": ["View", "Edit"], "scope": "class_section"},
            {"module_key": "homework", "actions": ["View"], "scope": "class_section"},
        ],
        change_summary="Approved staff permissions", actor_user_id=user.id,
    )
    publish_template_version(session, version_id=version.id, actor_user_id=user.id)
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app), engine, session, user, staff, version


def test_institution_role_builder_api_creates_roles_and_manages_multiple_assignments():
    admin = User(name="Admin", email="admin@api.test", password_hash="x", role="admin")
    client, engine, session, admin, staff, version = _client_for(admin)
    try:
        context = client.get("/api/institution/rbac/context")
        assert context.status_code == 200
        assert context.json()["institution_type"] == "school"

        templates = client.get("/api/institution/rbac/templates")
        assert templates.status_code == 200
        assert any(item["version_id"] == version.id for item in templates.json())

        created = client.post("/api/institution/rbac/roles", json={
            "role_key": "attendance_lead", "name": "Attendance Lead",
            "description": "Coordinates attendance", "template_version_id": version.id,
            "permissions": [
                {"module_key": "attendance", "action_key": "View", "scope": "class_section"},
                {"module_key": "attendance", "action_key": "Edit", "scope": "class_section"},
            ],
        })
        assert created.status_code == 201, created.text
        role_id = created.json()["id"]
        assert created.json()["source_template_version_id"] == version.id
        assert created.json()["active_assignment_count"] == 0

        users = client.get("/api/institution/rbac/users")
        assert users.status_code == 200
        assert [item["id"] for item in users.json()] == [staff.id]

        assigned = client.post("/api/institution/rbac/assignments", json={
            "user_id": staff.id, "role_id": role_id,
        })
        assert assigned.status_code == 201, assigned.text
        assert assigned.json()["role_name"] == "Attendance Lead"

        listing = client.get("/api/institution/rbac/assignments")
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["user_id"] == staff.id

        revoked = client.patch(f"/api/institution/rbac/assignments/{assigned.json()['id']}", json={
            "is_active": False,
        })
        assert revoked.status_code == 200, revoked.text
        assert revoked.json()["is_active"] is False
        assert client.get("/api/institution/rbac/assignments").json() == []

        events = set(session.scalars(select(AuditLog.event_type)).all())
        assert "rbac.institution_role.created" in events
        assert "rbac.role_assignment.created" in events
        assert "rbac.role_assignment.revoked" in events
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_institution_role_api_rejects_template_permission_escalation_and_wrong_role():
    admin = User(name="Admin", email="admin2@api.test", password_hash="x", role="admin")
    client, engine, session, admin, staff, version = _client_for(admin)
    try:
        response = client.post("/api/institution/rbac/roles", json={
            "role_key": "finance_admin", "name": "Finance Admin",
            "template_version_id": version.id,
            "permissions": [
                {"module_key": "fees", "action_key": "Delete", "scope": "institution"},
            ],
        })
        assert response.status_code == 422
        assert "exceeds the adopted template" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()

    teacher = User(name="Teacher", email="teacher2@api.test", password_hash="x", role="teacher")
    denied_client, denied_engine, denied_session, *_ = _client_for(teacher)
    try:
        response = denied_client.get("/api/institution/rbac/roles")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        denied_session.close()
        denied_engine.dispose()


def test_institution_role_api_hides_templates_for_other_institution_types():
    admin = User(name="College Admin", email="college@api.test", password_hash="x", role="admin")
    client, engine, session, admin, staff, version = _client_for(admin)
    try:
        from backend.app.models import School, RbacRoleTemplateVersion
        school = session.get(School, admin.school_id)
        school.institution_type = "college"
        session.commit()
        response = client.get("/api/institution/rbac/templates")
        assert response.status_code == 200
        assert all(item["version_id"] != version.id for item in response.json())
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
