from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.security import require_module_permission, require_roles


class EmptyPermissionStore:
    def scalar(self, statement):
        return None


def test_require_roles_does_not_expand_admin_to_every_school_role():
    checker = require_roles("super_admin", "admin")
    with pytest.raises(HTTPException) as exc:
        checker(user=SimpleNamespace(role="teacher"))
    assert exc.value.status_code == 403
    assert checker(user=SimpleNamespace(role="admin")).role == "admin"


def test_module_fallback_roles_are_exact():
    checker = require_module_permission("student-import", "Create", "admin")
    with pytest.raises(HTTPException) as exc:
        checker(user=SimpleNamespace(role="teacher", school_id=1), db=EmptyPermissionStore())
    assert exc.value.status_code == 403
    assert checker(user=SimpleNamespace(role="admin", school_id=1), db=EmptyPermissionStore()).role == "admin"


def test_otp_consumption_locks_the_challenge_and_marks_it_used():
    from datetime import datetime, timedelta
    from backend.app import main

    email = "person@example.test"
    code = "123456"
    record = SimpleNamespace(
        code_hash=main._otp_digest(email, code),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        attempts=0,
        used_at=None,
    )

    class LockedCodeStore:
        def __init__(self):
            self.commits = 0

        def scalar(self, statement):
            assert statement._for_update_arg is not None
            return record

        def commit(self):
            self.commits += 1

    db = LockedCodeStore()
    main._consume_auth_code(db, email, code, "login_mfa")
    assert record.used_at is not None
    assert db.commits == 1


def test_otp_consumption_counts_incorrect_attempts():
    from datetime import datetime, timedelta
    from backend.app import main

    email = "person@example.test"
    record = SimpleNamespace(
        code_hash=main._otp_digest(email, "correct"),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        attempts=0,
        used_at=None,
    )

    class CodeStore:
        def scalar(self, statement):
            return record

        def commit(self):
            pass

    with pytest.raises(HTTPException) as exc:
        main._consume_auth_code(CodeStore(), email, "wrong", "reset")
    assert exc.value.status_code == 400
    assert record.attempts == 1
    assert record.used_at is None
