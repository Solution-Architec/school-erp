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
