from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.database import Base
from backend.app import models
from backend.app.rbac_catalog import (
    ACTIONS,
    INSTITUTION_TYPES,
    LEGACY_ACTION_KEYS,
    MODULES,
    catalog_snapshot,
    seed_rbac_catalog,
)


def make_catalog_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_catalog_seed_registers_all_legacy_modules_and_institution_types():
    engine, db = make_catalog_session()
    try:
        counts = seed_rbac_catalog(db)
        db.commit()

        assert counts["modules"] == len(MODULES)
        assert counts["actions"] == len(ACTIONS)
        assert counts["institution_types"] == len(INSTITUTION_TYPES)
        assert {row.key for row in db.scalars(select(models.RbacModule)).all()} == {
            item[0] for item in MODULES
        }
        assert {row.key for row in db.scalars(select(models.RbacInstitutionType)).all()} == {
            "school", "college", "university", "coaching_centre", "training_institute", "other"
        }
        assert db.get(models.RbacModule, "developer-control").is_platform_only is True
        assert db.get(models.RbacModule, "schools").is_platform_only is True
    finally:
        db.close()
        engine.dispose()


def test_catalog_seed_is_idempotent_and_preserves_developer_metadata():
    engine, db = make_catalog_session()
    try:
        first = seed_rbac_catalog(db)
        db.commit()
        module = db.get(models.RbacModule, "attendance")
        module.label = "Custom attendance label"
        module.is_active = False
        db.commit()

        second = seed_rbac_catalog(db)
        db.commit()

        assert first["modules"] == len(MODULES)
        assert second == {
            "institution_types": 0,
            "modules": 0,
            "actions": 0,
            "module_actions": 0,
        }
        preserved = db.get(models.RbacModule, "attendance")
        assert preserved.label == "Custom attendance label"
        assert preserved.is_active is False
    finally:
        db.close()
        engine.dispose()


def test_catalog_exposes_legacy_action_combinations_without_granting_permissions():
    engine, db = make_catalog_session()
    try:
        seed_rbac_catalog(db)
        db.commit()

        combinations = db.scalars(select(models.RbacModuleAction)).all()
        assert len(combinations) == len(MODULES) * len(LEGACY_ACTION_KEYS)
        assert {item.action_key for item in combinations} == set(LEGACY_ACTION_KEYS)

        snapshot = catalog_snapshot(db)
        assert all(not module["platform_only"] for module in snapshot["modules"])
        assert "developer-control" not in {module["key"] for module in snapshot["modules"]}
        assert "schools" not in {module["key"] for module in snapshot["modules"]}
        assert len(snapshot["actions"]) == len(ACTIONS)
    finally:
        db.close()
        engine.dispose()



def test_catalog_module_keys_match_the_existing_authorization_registry():
    from backend.app.main import RBAC_MODULES

    assert {item[0] for item in MODULES} == RBAC_MODULES
