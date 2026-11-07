import os
from types import SimpleNamespace

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-that-is-at-least-32-characters-long")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")

import pytest
from fastapi import HTTPException

from app import security


class FakeDB:
    def __init__(self, user):
        self.user = user

    def get(self, model, user_id):
        return self.user if self.user and self.user.id == user_id else None


def test_access_token_contains_user_token_version():
    user = SimpleNamespace(id=7, role="teacher", token_version=3)
    token = security.create_access_token(user)
    payload = security.jwt.decode(token, security.JWT_SECRET_KEY, algorithms=[security.JWT_ALGORITHM])
    assert payload["sub"] == "7"
    assert payload["ver"] == 3


def test_current_user_accepts_current_token_version():
    user = SimpleNamespace(id=7, role="teacher", token_version=2, is_active=True)
    token = security.create_access_token(user)
    assert security.current_user(token=token, db=FakeDB(user)) is user


def test_current_user_rejects_revoked_token():
    old_token_user = SimpleNamespace(id=7, role="teacher", token_version=0)
    token = security.create_access_token(old_token_user)
    current_user = SimpleNamespace(id=7, role="teacher", token_version=1, is_active=True)
    with pytest.raises(HTTPException) as exc:
        security.current_user(token=token, db=FakeDB(current_user))
    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail.lower()


def test_teacher_defaults_do_not_grant_finance_or_delete():
    assert not security.default_role_permission("teacher", "payments", "Create")
    assert not security.default_role_permission("teacher", "fee-reports", "View")
    assert not security.default_role_permission("teacher", "students", "Delete")


def test_unknown_role_and_action_fail_closed():
    assert not security.default_role_permission("unknown-role", "students", "View")
    assert not security.default_role_permission("teacher", "students", "Export")
