#!/usr/bin/env python3
"""Keep daily, weekly and monthly PostgreSQL recovery points."""
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

root = Path(os.environ.get("BACKUP_DIR", "/backups"))
prefix = os.environ.get("BACKUP_PREFIX", "school_erp")
daily_days = int(os.environ.get("BACKUP_DAILY_RETENTION_DAYS", "7"))
weekly_weeks = int(os.environ.get("BACKUP_WEEKLY_RETENTION_WEEKS", "4"))
monthly_months = int(os.environ.get("BACKUP_MONTHLY_RETENTION_MONTHS", "12"))
pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{8}}T\d{{6}}Z)_\d+_backup\.dump$")
now = datetime.now(timezone.utc)
archives = []
for path in root.glob(f"{prefix}_*_backup.dump"):
    match = pattern.match(path.name)
    if not match:
        continue
    try:
        stamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        continue
    archives.append((stamp, path))
archives.sort(reverse=True)
keep = set()
daily_cutoff = now - timedelta(days=daily_days)
weekly_cutoff = now - timedelta(weeks=weekly_weeks)
monthly_cutoff = now - timedelta(days=monthly_months * 31)
seen_days, seen_weeks, seen_months = set(), set(), set()
for stamp, path in archives:
    day = stamp.date()
    week = (stamp.isocalendar().year, stamp.isocalendar().week)
    month = (stamp.year, stamp.month)
    if stamp >= daily_cutoff and day not in seen_days:
        keep.add(path); seen_days.add(day)
    if stamp >= weekly_cutoff and week not in seen_weeks:
        keep.add(path); seen_weeks.add(week)
    if stamp >= monthly_cutoff and month not in seen_months:
        keep.add(path); seen_months.add(month)
for _, path in archives:
    if path not in keep:
        path.unlink(missing_ok=True)
