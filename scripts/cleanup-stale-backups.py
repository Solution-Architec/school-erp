#!/usr/bin/env python3
"""Remove abandoned backup partials without deleting a running backup."""
import os
import re
import time
from pathlib import Path

root = Path(os.getenv("BACKUP_DIR", "/backups"))
prefix = os.getenv("BACKUP_PREFIX", "school_erp")
stale_hours = max(1, int(os.getenv("BACKUP_PARTIAL_STALE_HOURS", "48")))
pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{8}}T\d{{6}}Z)_(\d+)_backup\.dump\.partial$")
cutoff = time.time() - stale_hours * 3600
removed = 0
for path in root.glob(f"{prefix}_*.dump.partial"):
    match = pattern.match(path.name)
    if not match:
        continue
    try:
        if path.stat().st_mtime >= cutoff:
            continue
        pid = int(match.group(1))
        try:
            os.kill(pid, 0)
            continue
        except ProcessLookupError:
            pass
        except PermissionError:
            continue
        path.unlink()
        removed += 1
    except FileNotFoundError:
        continue
print(f"Removed {removed} stale inactive partial backup(s)")
