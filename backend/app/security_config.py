"""Fail-closed configuration validation for authentication secrets."""

import os


_MIN_JWT_SECRET_BYTES = 32
_PLACEHOLDER_MARKERS = (
    "unsafe-development-secret",
    "replace-with",
    "replace-this",
    "change-me",
    "changeme",
    "your-secret",
    "example-secret",
    "placeholder",
)


def load_jwt_secret(value: str | None = None) -> str:
    """Return a strong configured JWT secret or fail closed.

    The secret must contain at least 256 bits (32 UTF-8 bytes). Generate one
    with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    """
    candidate = os.getenv("JWT_SECRET_KEY") if value is None else value
    if candidate is None or not candidate.strip():
        raise RuntimeError(
            "JWT_SECRET_KEY is required. Generate a unique secret with "
            "'python -c \"import secrets; print(secrets.token_urlsafe(48))\"'."
        )

    secret = candidate.strip()
    if len(secret.encode("utf-8")) < _MIN_JWT_SECRET_BYTES:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 UTF-8 bytes.")

    lowered = secret.lower()
    if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
        raise RuntimeError("JWT_SECRET_KEY contains a known placeholder value.")

    return secret
