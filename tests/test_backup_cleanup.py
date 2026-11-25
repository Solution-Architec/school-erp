import os
import subprocess
import sys
import time
from pathlib import Path


def test_cleanup_removes_only_old_inactive_matching_partials(tmp_path):
    prefix = "school_erp"
    stale = tmp_path / f"{prefix}_20200101T000000Z_99999999_backup.dump.partial"
    recent = tmp_path / f"{prefix}_20200101T000000Z_99999998_backup.dump.partial"
    unrelated = tmp_path / "other_20200101T000000Z_99999997_backup.dump.partial"
    active = tmp_path / f"{prefix}_20200101T000000Z_{os.getpid()}_backup.dump.partial"
    active_marker = tmp_path / ".backup-active-777"
    for item in (stale, recent, unrelated, active):
        item.write_bytes(b"partial")
    old = time.time() - 72 * 3600
    os.utime(stale, (old, old))
    active_marker.write_text("running")
    os.utime(active_marker, (time.time(), time.time()))
    env = os.environ | {"BACKUP_DIR": str(tmp_path), "BACKUP_PREFIX": prefix, "BACKUP_PARTIAL_STALE_HOURS": "48"}

    # A fresh shared marker means another container may be writing a partial:
    # cleanup must leave every partial untouched in that case.
    subprocess.run([sys.executable, "scripts/cleanup-stale-backups.py"], check=True, env=env)
    assert stale.exists()
    assert recent.exists()
    assert unrelated.exists()
    assert active.exists()

    # Once the marker is gone, only old, matching, inactive partials are removed.
    active_marker.unlink()
    subprocess.run([sys.executable, "scripts/cleanup-stale-backups.py"], check=True, env=env)
    assert not stale.exists()
    assert recent.exists()
    assert unrelated.exists()
    assert active.exists()
