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
    checker = require_module_permission("students", "Create", "admin")
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


def test_school_account_approval_fallback_excludes_regular_staff():
    checker = require_module_permission("approvals", "Approve", "admin", "principal", "vice_principal")
    with pytest.raises(HTTPException) as exc:
        checker(user=SimpleNamespace(role="teacher", school_id=1), db=EmptyPermissionStore())
    assert exc.value.status_code == 403
    assert checker(user=SimpleNamespace(role="principal", school_id=1), db=EmptyPermissionStore()).role == "principal"


def test_default_module_policy_blocks_cross_role_module_access():
    teacher = SimpleNamespace(role="teacher", school_id=7)
    with pytest.raises(HTTPException) as exc:
        require_module_permission("payments", "View", "teacher")(user=teacher, db=EmptyPermissionStore())
    assert exc.value.status_code == 403
    assert require_module_permission("attendance", "View", "teacher")(user=teacher, db=EmptyPermissionStore()).role == "teacher"


def test_default_module_policy_limits_parent_to_view_and_create():
    parent = SimpleNamespace(role="parent", school_id=7)
    assert require_module_permission("parent-messages", "Create", "parent")(user=parent, db=EmptyPermissionStore()).role == "parent"
    with pytest.raises(HTTPException) as exc:
        require_module_permission("parent-messages", "Delete", "parent")(user=parent, db=EmptyPermissionStore())
    assert exc.value.status_code == 403


def test_explicit_permission_grant_can_override_default_role_matrix():
    teacher = SimpleNamespace(role="teacher", school_id=7)
    class GrantStore:
        def __init__(self):
            self.calls = 0
        def scalar(self, statement):
            self.calls += 1
            return None if self.calls == 1 else SimpleNamespace(enabled=True)
    assert require_module_permission("payments", "View", "teacher")(user=teacher, db=GrantStore()).role == "teacher"


def test_school_level_explicit_deny_overrides_global_grant():
    teacher = SimpleNamespace(role="teacher", school_id=7)
    class GrantStore:
        def scalar(self, statement):
            return SimpleNamespace(enabled=False)
    with pytest.raises(HTTPException) as exc:
        require_module_permission("attendance", "View", "teacher")(user=teacher, db=GrantStore())
    assert exc.value.status_code == 403


def test_default_delete_permission_is_limited_to_admin():
    admin = SimpleNamespace(role="admin", school_id=3)
    principal = SimpleNamespace(role="principal", school_id=3)
    assert require_module_permission("students", "Delete", "admin")(user=admin, db=EmptyPermissionStore()).role == "admin"
    with pytest.raises(HTTPException) as exc:
        require_module_permission("students", "Delete", "super_admin", "admin")(user=principal, db=EmptyPermissionStore())
    assert exc.value.status_code == 403


def test_teacher_can_write_academic_records_but_not_student_profiles():
    teacher = SimpleNamespace(role="teacher", school_id=4)
    assert require_module_permission("attendance", "Create", "teacher")(user=teacher, db=EmptyPermissionStore()).role == "teacher"
    with pytest.raises(HTTPException) as exc:
        require_module_permission("students", "Create", "teacher")(user=teacher, db=EmptyPermissionStore())
    assert exc.value.status_code == 403


def test_accountant_and_transport_manager_have_separate_write_scopes():
    accountant = SimpleNamespace(role="accountant", school_id=4)
    transport = SimpleNamespace(role="transport_manager", school_id=4)
    assert require_module_permission("fee-structures", "Create", "accountant")(user=accountant, db=EmptyPermissionStore()).role == "accountant"
    with pytest.raises(HTTPException):
        require_module_permission("students", "Create", "accountant")(user=accountant, db=EmptyPermissionStore())
    assert require_module_permission("vehicles", "Create", "transport_manager")(user=transport, db=EmptyPermissionStore()).role == "transport_manager"
    with pytest.raises(HTTPException):
        require_module_permission("fee-structures", "Create", "transport_manager")(user=transport, db=EmptyPermissionStore())


def test_clerk_can_create_student_but_cannot_delete_records_by_default():
    clerk = SimpleNamespace(role="clerk", school_id=4)
    assert require_module_permission("students", "Create", "clerk")(user=clerk, db=EmptyPermissionStore()).role == "clerk"
    with pytest.raises(HTTPException):
        require_module_permission("students", "Delete", "admin", "clerk")(user=clerk, db=EmptyPermissionStore())


def test_admin_cannot_delete_library_loan_history():
    admin = SimpleNamespace(role="admin", school_id=4)
    with pytest.raises(HTTPException):
        require_module_permission("library-loans", "Delete", "admin")(user=admin, db=EmptyPermissionStore())


def test_read_only_roles_cannot_create_or_edit_records():
    guard = SimpleNamespace(role="security_guard", school_id=4)
    assert require_module_permission("students", "View", "security_guard")(user=guard, db=EmptyPermissionStore()).role == "security_guard"
    with pytest.raises(HTTPException):
        require_module_permission("students", "Create", "security_guard")(user=guard, db=EmptyPermissionStore())
    with pytest.raises(HTTPException):
        require_module_permission("students", "Edit", "security_guard")(user=guard, db=EmptyPermissionStore())


def test_parent_can_submit_but_not_edit_leave_requests():
    parent = SimpleNamespace(role="parent", school_id=4)
    assert require_module_permission("student-leave", "Create", "parent")(user=parent, db=EmptyPermissionStore()).role == "parent"
    with pytest.raises(HTTPException):
        require_module_permission("student-leave", "Edit", "parent")(user=parent, db=EmptyPermissionStore())
