import pytest
from pydantic import ValidationError

from backend.app.platform_operations import (
    ClientRequestDecision,
    IncidentInput,
    MaintenanceWindowInput,
    _role_allowed,
)


def test_institution_role_assignment_is_scoped_to_institution_type():
    assert _role_allowed("school_hod", "school")
    assert _role_allowed("college_admin", "college")
    assert _role_allowed("university_admin", "university")
    assert _role_allowed("trainer", "training_institute")
    assert not _role_allowed("college_hod", "school")
    assert not _role_allowed("research_scholar", "college")
    assert not _role_allowed("school_student", "university")


def test_client_request_decision_requires_supported_action():
    assert ClientRequestDecision(decision="approve").decision == "approve"
    with pytest.raises(ValidationError):
        ClientRequestDecision(decision="activate")


def test_institution_incident_requires_school_id_at_route_boundary():
    item = IncidentInput(title="Client database issue", affected_scope="institution")
    assert item.school_id is None


def test_maintenance_window_rejects_missing_title():
    with pytest.raises(ValidationError):
        MaintenanceWindowInput(
            title="",
            starts_at="2026-12-01T01:00:00",
            ends_at="2026-12-01T02:00:00",
        )
