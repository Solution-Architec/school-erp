import pytest

from backend.app.security_config import load_jwt_secret


def test_missing_jwt_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY is required"):
        load_jwt_secret()


@pytest.mark.parametrize("value", [
    "",
    "short",
    "replace-this-with-a-long-random-secret-at-least-32-characters",
    "unsafe-development-secret-change-me",
])
def test_weak_or_placeholder_jwt_secret_is_rejected(value):
    with pytest.raises(RuntimeError):
        load_jwt_secret(value)


def test_strong_jwt_secret_is_accepted():
    secret = "a" * 32
    assert load_jwt_secret(secret) == secret


def test_secret_is_trimmed():
    secret = "b" * 40
    assert load_jwt_secret(f"  {secret}  ") == secret
