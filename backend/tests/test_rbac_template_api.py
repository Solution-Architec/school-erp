from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import AuditLog, User
from backend.app.rbac_catalog import seed_rbac_catalog
from backend.app.security import current_user


def _client_for(user):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    seed_rbac_catalog(session)
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app), engine, session


def _make_user(role):
    return User(name=role, email=f"{role}@api.test", password_hash="x", role=role)


def test_developer_template_api_lifecycle_and_audit():
    # Create the identity in the same test DB before installing dependency overrides.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    seed_rbac_catalog(session)
    developer = _make_user("super_admin")
    session.add(developer)
    session.commit()
    app.dependency_overrides[get_db] = lambda: iter([session])
    app.dependency_overrides[current_user] = lambda: developer
    client = TestClient(app)
    try:
        created = client.post("/api/developer/rbac/templates", json={
            "template_key": "api_teacher", "name": "API Teacher",
            "description": "Template created through the developer API",
            "category": "academic",
        })
        assert created.status_code == 201, created.text
        template_id = created.json()["id"]

        draft = client.post(f"/api/developer/rbac/templates/{template_id}/versions", json={
            "institution_types": ["school"],
            "permissions": [{
                "module_key": "attendance", "actions": ["View"],
                "scope": "class_section",
            }],
            "change_summary": "Initial API version",
        })
        assert draft.status_code == 201, draft.text
        version_id = draft.json()["id"]
        assert draft.json()["status"] == "draft"

        published = client.post(f"/api/developer/rbac/versions/{version_id}/publish")
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "published"

        listing = client.get("/api/developer/rbac/templates")
        assert listing.status_code == 200
        assert listing.json()[0]["versions"][0]["status"] == "published"

        retired = client.post(f"/api/developer/rbac/versions/{version_id}/retire")
        assert retired.status_code == 200, retired.text
        assert retired.json()["status"] == "retired"

        events = set(session.scalars(select(AuditLog.event_type)).all())
        assert {
            "rbac.template.created",
            "rbac.template.version.created",
            "rbac.template.version.published",
            "rbac.template.version.retired",
        }.issubset(events)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_developer_template_api_rejects_non_developer_users():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    teacher = _make_user("teacher")
    session.add(teacher)
    session.commit()
    app.dependency_overrides[get_db] = lambda: iter([session])
    app.dependency_overrides[current_user] = lambda: teacher
    client = TestClient(app)
    try:
        response = client.get("/api/developer/rbac/templates")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
