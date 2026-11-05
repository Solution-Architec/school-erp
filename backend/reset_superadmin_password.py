"""Interactively reset a global Super Admin password.

Run from the backend directory (or the backend container working directory):
    python reset_superadmin_password.py [email]

The password is prompted without echo and is never read from an environment
variable or written to a file. This only updates an existing global
super_admin account (school_id IS NULL).
"""
import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app import models
from app.database import SessionLocal
from app.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset a global Super Admin password.")
    parser.add_argument(
        "email",
        nargs="?",
        default=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com"),
        help="Super Admin email (defaults to BOOTSTRAP_ADMIN_EMAIL or admin@example.com)",
    )
    args = parser.parse_args()
    email = args.email.strip().lower()

    try:
        password = getpass.getpass("New password: ")
        confirmation = getpass.getpass("Confirm new password: ")
    except (EOFError, OSError):
        print(
            "ERROR: An interactive terminal is required. "
            "Run without docker compose exec -T.",
            file=sys.stderr,
        )
        return 2

    if password != confirmation:
        print("ERROR: Passwords do not match.", file=sys.stderr)
        return 2
    if len(password) < 12:
        print("ERROR: Use at least 12 characters.", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        user = db.scalar(
            select(models.User).where(
                models.User.email == email,
                models.User.role == "super_admin",
                models.User.school_id.is_(None),
            )
        )
        if user is None:
            print(f"ERROR: Global Super Admin account not found for {email}.", file=sys.stderr)
            return 1

        user.password_hash = hash_password(password)
        db.commit()

    print(f"SUCCESS: Password updated for global Super Admin {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
