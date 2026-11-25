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
    for item in (stale, recent, unrelated, active):
        item.write_bytes(b"partial")
    old = time.time() - 72 * 3600
    os.utime(stale, (old, old))
    env = os.environ | {"BACKUP_DIR": str(tmp_path), "BACKUP_PREFIX": prefix, "BACKUP_PARTIAL_STALE_HOURS": "48"}
    subprocess.run([sys.executable, "scripts/cleanup-stale-backups.py"], check=True, env=env)
    assert not stale.exists()
    assert recent.exists()
    assert unrelated.exists()
    assert active.exists()
