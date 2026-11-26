import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app import models
from app.rbac_catalog import seed_rbac_catalog
from app.rbac_templates import (
    create_role_template,
    create_template_version,
    publish_template_version,
    replace_draft_policy,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(models.User(
            name="Developer", email="developer@example.test",
            password_hash="not-a-real-password", role="super_admin",
        ))
        session.flush()
        seed_rbac_catalog(session)
        session.commit()
        yield session
    engine.dispose()


def _template(db):
    user_id = db.scalar(select(models.User.id))
    template = create_role_template(
        db, template_key="school_teacher", name="School Teacher",
        description="Teaching role", category="academic", actor_user_id=user_id,
    )
    db.commit()
    return template, user_id


def _policy():
    return [{
        "module_key": "attendance",
        "actions": ["View", "Edit"],
        "scope": "class_section",
    }]


def test_create_and_publish_immutable_template_version(db):
    template, user_id = _template(db)
    version = create_template_version(
        db, template_id=template.id, institution_types=["school"],
        permissions=_policy(), change_summary="Initial teacher template",
        actor_user_id=user_id,
    )
    assert version.version_number == 1
    assert version.status == "draft"
    published = publish_template_version(db, version_id=version.id, actor_user_id=user_id)
    db.commit()

    assert published.status == "published"
    assert published.published_by == user_id
    assert published.published_at is not None
    with pytest.raises(ValueError, match="immutable"):
        replace_draft_policy(
            db, version_id=version.id, institution_types=["school"],
            permissions=_policy(), change_summary="Attempted rewrite",
        )
    with pytest.raises(ValueError, match="Only a draft"):
        publish_template_version(db, version_id=version.id, actor_user_id=user_id)


def test_new_version_is_created_instead_of_rewriting_published_version(db):
    template, user_id = _template(db)
    first = create_template_version(
        db, template_id=template.id, institution_types=["school"],
        permissions=_policy(), change_summary="v1", actor_user_id=user_id,
    )
    publish_template_version(db, version_id=first.id, actor_user_id=user_id)
    second = create_template_version(
        db, template_id=template.id, institution_types=["school", "college"],
        permissions=_policy(), change_summary="Add college applicability",
        actor_user_id=user_id,
    )
    assert second.version_number == 2
    assert second.status == "draft"
    assert first.status == "published"


@pytest.mark.parametrize("module_key", ["developer-control", "schools"])
def test_tenant_template_rejects_platform_only_modules(db, module_key):
    template, user_id = _template(db)
    with pytest.raises(ValueError, match="Platform-only"):
        create_template_version(
            db, template_id=template.id, institution_types=["school"],
            permissions=[{"module_key": module_key, "actions": ["View"], "scope": "institution"}],
            change_summary="Must be rejected", actor_user_id=user_id,
        )


def test_template_rejects_unknown_actions_and_scopes(db):
    template, user_id = _template(db)
    with pytest.raises(ValueError, match="not allowed"):
        create_template_version(
            db, template_id=template.id, institution_types=["school"],
            permissions=[{"module_key": "attendance", "actions": ["Manage"], "scope": "institution"}],
            change_summary="Invalid action", actor_user_id=user_id,
        )
    with pytest.raises(ValueError, match="Unsupported data scope"):
        create_template_version(
            db, template_id=template.id, institution_types=["school"],
            permissions=[{"module_key": "attendance", "actions": ["View"], "scope": "global"}],
            change_summary="Invalid scope", actor_user_id=user_id,
        )


def test_draft_policy_can_be_replaced_and_template_key_is_unique(db):
    template, user_id = _template(db)
    draft = create_template_version(
        db, template_id=template.id, institution_types=["school"],
        permissions=_policy(), change_summary="Draft", actor_user_id=user_id,
    )
    replace_draft_policy(
        db, version_id=draft.id, institution_types=["school"],
        permissions=[{"module_key": "attendance", "actions": ["View"], "scope": "institution"}],
        change_summary="Narrowed draft",
    )
    assert draft.permissions[0]["actions"] == ["View"]
    with pytest.raises(ValueError, match="already exists"):
        create_role_template(
            db, template_key="school_teacher", name="Duplicate",
            description="", category="academic", actor_user_id=user_id,
        )
