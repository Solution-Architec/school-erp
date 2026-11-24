from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.security import require_module_permission, require_roles


class EmptyPermissionStore:
    def scalar(self, statement):
        return None


def test_platform_workspace_has_tenant_admin_permissions_without_platform_admin_role():
    workspace_user = SimpleNamespace(
        id=7, role="admin", school_id=21,
        is_platform_workspace=True, platform_owner_id=7,
    )
    checker = require_module_permission("students", "Edit")
    assert checker(user=workspace_user, db=EmptyPermissionStore()) is workspace_user

    platform_only = require_roles("super_admin")
    with pytest.raises(HTTPException) as exc:
        platform_only(user=workspace_user)
    assert exc.value.status_code == 403


def test_workspace_token_resolves_only_for_active_platform_owner(monkeypatch):
    from backend.app import security
    from backend.app.models import User, School

    owner = SimpleNamespace(
        id=7, name="Platform Owner", email="owner@example.test",
        role="super_admin", is_active=True,
    )
    school = SimpleNamespace(id=21, name="Client College", is_active=True)

    class FakeDB:
        def get(self, model, item_id):
            if model is User and item_id == 7:
                return owner
            if model is School and item_id == 21:
                return school
            return None

    monkeypatch.setattr(
        security.jwt, "decode",
        lambda *args, **kwargs: {"sub": "7", "workspace_school_id": 21},
    )
    workspace = security.current_user(token="signed-token", db=FakeDB())
    assert workspace.role == "admin"
    assert workspace.school_id == 21
    assert workspace.platform_owner_id == 7
    assert workspace.is_platform_workspace is True


def test_workspace_token_rejects_non_platform_owner(monkeypatch):
    from backend.app import security
    from backend.app.models import User, School

    ordinary_user = SimpleNamespace(id=8, role="admin", is_active=True)
    school = SimpleNamespace(id=21, name="Client College", is_active=True)

    class FakeDB:
        def get(self, model, item_id):
            if model is User:
                return ordinary_user
            if model is School:
                return school
            return None

    monkeypatch.setattr(
        security.jwt, "decode",
        lambda *args, **kwargs: {"sub": "8", "workspace_school_id": 21},
    )
    with pytest.raises(HTTPException) as exc:
        security.current_user(token="signed-token", db=FakeDB())
    assert exc.value.status_code == 403


def test_platform_quotation_rejects_discount_above_total():
    from backend.app.platform_control import QuotationInput

    with pytest.raises(ValidationError):
        QuotationInput(
            school_id=1, title="Annual subscription",
            amount=Decimal("1000"), tax_amount=Decimal("100"),
            discount_amount=Decimal("1200"),
        )


def test_platform_subscription_rejects_expiry_before_start():
    from backend.app.platform_control import SubscriptionInput

    with pytest.raises(ValidationError):
        SubscriptionInput(
            school_id=1, plan_name="Annual",
            amount=Decimal("12000"), billing_cycle="annual",
            start_date=date(2026, 4, 1), end_date=date(2026, 3, 31),
        )
