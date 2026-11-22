"""Secure first-run bootstrap administrator configuration."""

import os


_PLACEHOLDER_MARKERS = (
    "change-me",
    "changeme",
    "replace-with",
    "replace-this",
    "password123",
    "example-password",
    "placeholder",
)


def load_bootstrap_admin_config(env: dict[str, str] | None = None) -> dict[str, str]:
    """Require explicitly supplied credentials for the first super-admin account."""
    source = os.environ if env is None else env
    email = source.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = source.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    name = source.get("BOOTSTRAP_ADMIN_NAME", "ERP Administrator").strip()

    if not email or not password:
        raise RuntimeError(
            "No super administrator exists. Set BOOTSTRAP_ADMIN_EMAIL and "
            "BOOTSTRAP_ADMIN_PASSWORD to provision the initial administrator."
        )
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise RuntimeError("BOOTSTRAP_ADMIN_EMAIL must be a valid email address.")
    if len(password) < 16:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must be at least 16 characters.")
    if any(marker in password.lower() for marker in _PLACEHOLDER_MARKERS):
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD contains a known placeholder value.")
    if not name:
        raise RuntimeError("BOOTSTRAP_ADMIN_NAME cannot be empty.")

    return {"email": email, "password": password, "name": name}
