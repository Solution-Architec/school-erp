import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def test_retention_keeps_recent_daily_and_removes_out_of_policy_archives(tmp_path):
    now = datetime.now(timezone.utc)
    recent = now.strftime("%Y%m%dT%H%M%SZ")
    old = (now - timedelta(days=75)).strftime("%Y%m%dT%H%M%SZ")
    keep = tmp_path / f"school_erp_{recent}_123_backup.dump"
    remove = tmp_path / f"school_erp_{old}_124_backup.dump"
    keep.write_bytes(b"verified")
    remove.write_bytes(b"old")
    env = os.environ | {
        "BACKUP_DIR": str(tmp_path), "BACKUP_PREFIX": "school_erp",
        "BACKUP_DAILY_RETENTION_DAYS": "7", "BACKUP_WEEKLY_RETENTION_WEEKS": "4",
        "BACKUP_MONTHLY_RETENTION_MONTHS": "2",
    }
    subprocess.run([sys.executable, "scripts/backup-retention.py"], check=True, env=env)
    assert keep.exists()
    assert not remove.exists()
