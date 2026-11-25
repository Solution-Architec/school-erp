import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "platform_monitor", Path(__file__).parents[1] / "monitoring" / "platform-monitor.py"
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def test_monitor_transitions_alert_once_and_recovers():
    previous = {"failures": {"smtp": {"status": "critical"}}}
    current = {"smtp": {"status": "ok"}, "application": {"status": "warning"}}
    failures, new, recovered = monitor.classify_transitions(previous, current)
    assert set(failures) == {"application"}
    assert set(new) == {"application"}
    assert recovered == ["smtp"]


def test_unconfigured_integrations_are_partial_not_healthy():
    assert monitor.overall_status({"smtp": {"status": "not_configured"}}) == "partial"
    assert monitor.overall_status({"smtp": {"status": "ok"}}) == "healthy"
    assert monitor.overall_status({"smtp": {"status": "critical"}}) == "critical"


def test_resource_thresholds_flag_disk_pressure(monkeypatch):
    monkeypatch.setenv("MONITOR_DISK_WARNING_PERCENT", "80")
    monkeypatch.setenv("MONITOR_DISK_CRITICAL_PERCENT", "90")
    result = monitor.apply_resource_thresholds({}, {
        "host_disk_used_percent": 93, "backup_disk_used_percent": 55,
        "memory_used_percent": 30, "cpu_load_per_core": 0.2,
    })
    assert result["host_disk"]["status"] == "critical"
    assert result["backup_disk"]["status"] == "ok"
