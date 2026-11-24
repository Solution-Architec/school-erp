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



def test_platform_audit_helper_records_structured_event():
    import json
    from types import SimpleNamespace

    from backend.app.platform_operations import _audit

    class AuditCollector:
        def add(self, record):
            self.record = record

    collector = AuditCollector()
    _audit(
        collector,
        SimpleNamespace(id=42),
        "platform.test.event",
        "school",
        "17",
        {"action": "verified", "count": 2},
    )

    assert collector.record.actor_user_id == 42
    assert collector.record.event_type == "platform.test.event"
    assert collector.record.target_type == "school"
    assert collector.record.target_id == "17"
    assert json.loads(collector.record.details) == {"action": "verified", "count": 2}


def test_backup_health_reports_unconfigured_and_missing_directory(tmp_path):
    from backend.app.platform_operations import _backup_health

    assert _backup_health(None)["status"] == "not_configured"
    missing = _backup_health(str(tmp_path / "missing"))
    assert missing["configured"] is True
    assert missing["status"] == "directory_missing"


def test_backup_health_waits_for_first_backup(tmp_path):
    from backend.app.platform_operations import _backup_health

    result = _backup_health(str(tmp_path))
    assert result["status"] == "awaiting_first_backup"
    assert result["verified"] is False


def test_backup_health_marks_restore_tested_dump_healthy_and_stale(tmp_path):
    import os
    from backend.app.platform_operations import _backup_health

    dump = tmp_path / "school_erp_20261124T000000Z.dump"
    dump.write_bytes(b"test archive marker")
    now = 1_800_000_000.0
    os.utime(dump, (now - 3600, now - 3600))

    healthy = _backup_health(str(tmp_path), now=now, max_age_hours=26)
    assert healthy["status"] == "healthy"
    assert healthy["verified"] is True
    assert healthy["verification"] == "restore_tested"

    stale = _backup_health(str(tmp_path), now=now, max_age_hours=0.5)
    assert stale["status"] == "stale"


def test_backup_health_does_not_claim_legacy_sql_is_restore_tested(tmp_path):
    import os
    from backend.app.platform_operations import _backup_health

    legacy = tmp_path / "legacy.sql"
    legacy.write_text("-- legacy backup")
    now = 1_800_000_000.0
    os.utime(legacy, (now - 60, now - 60))

    result = _backup_health(str(tmp_path), now=now, max_age_hours=26)
    assert result["status"] == "verification_unknown"
    assert result["verified"] is False
