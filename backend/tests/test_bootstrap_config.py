import pytest

from backend.app.bootstrap_config import load_bootstrap_admin_config


def test_bootstrap_requires_explicit_email_and_password():
    with pytest.raises(RuntimeError, match="No super administrator exists"):
        load_bootstrap_admin_config({})


@pytest.mark.parametrize("password", [
    "",
    "short",
    "replace-with-a-strong-password",
    "ChangeMe123!ChangeMe123!",
])
def test_bootstrap_rejects_weak_or_placeholder_password(password):
    with pytest.raises(RuntimeError):
        load_bootstrap_admin_config({
            "BOOTSTRAP_ADMIN_EMAIL": "admin@example.org",
            "BOOTSTRAP_ADMIN_PASSWORD": password,
        })


def test_bootstrap_rejects_invalid_email():
    with pytest.raises(RuntimeError, match="valid email"):
        load_bootstrap_admin_config({
            "BOOTSTRAP_ADMIN_EMAIL": "not-an-email",
            "BOOTSTRAP_ADMIN_PASSWORD": "a-unique-strong-password",
        })


def test_bootstrap_accepts_explicit_strong_credentials():
    config = load_bootstrap_admin_config({
        "BOOTSTRAP_ADMIN_EMAIL": "owner@example.org",
        "BOOTSTRAP_ADMIN_PASSWORD": "a-unique-strong-password",
        "BOOTSTRAP_ADMIN_NAME": "Initial Owner",
    })
    assert config == {
        "email": "owner@example.org",
        "password": "a-unique-strong-password",
        "name": "Initial Owner",
    }


def test_bootstrap_uses_default_display_name_only():
    config = load_bootstrap_admin_config({
        "BOOTSTRAP_ADMIN_EMAIL": "owner@example.org",
        "BOOTSTRAP_ADMIN_PASSWORD": "a-unique-strong-password",
    })
    assert config["name"] == "ERP Administrator"
