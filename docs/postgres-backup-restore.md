# PostgreSQL local backup and restore operations

## Local PC storage

The `db-backup` Compose service stores verified PostgreSQL backups directly in the project folder:

```text
~/school-erp/backups/
```

This is a host bind mount (`./backups:/backups`), not a Docker named volume. You can browse, copy, and archive the dump files directly from your PC. The backend mounts the same directory read-only so it can inspect backup status.

The service creates a compressed PostgreSQL 16 custom-format dump, validates it, restores it into a disposable isolated PostgreSQL instance, and publishes it only after restore verification succeeds. It then writes `backup-status.json` and applies daily, weekly, and monthly retention.

No AWS account, S3 bucket, or AWS credentials are required for local-only backups. Optional offsite S3/S3-compatible replication can be enabled with `BACKUP_S3_URI` and credentials in the untracked `.env` file; see [platform reliability monitoring](platform-reliability-monitoring.md).

## Host directory permissions

The container writes files as its unprivileged `postgres` user and uses your PC user’s primary group ID for group-readable backup files. Set this in the project-root `.env` file:

```dotenv
BACKUP_GID=1000
BACKUP_INTERVAL_SECONDS=86400
BACKUP_DAILY_RETENTION_DAYS=7
BACKUP_WEEKLY_RETENTION_WEEKS=4
BACKUP_MONTHLY_RETENTION_MONTHS=12
BACKUP_RUN_ON_START=true
BACKUP_PREFIX=school_erp
```

Replace `1000` with the output of `id -g` on your PC if it is different. Backup files are group-readable by your PC user and are not world-readable. Do not put AWS keys in this configuration.

## Start and inspect

Run from the project root:

```bash
mkdir -p backups
docker compose up -d --build db-backup
docker compose logs --tail=100 db-backup
ls -lah backups
cat backups/backup-status.json
```

A successful local backup has a `*_backup.dump` archive and a status file containing `"restore_verified":true`. When offsite storage is configured, also require `"offsite_status":"restore_verified"` before treating the remote copy as recoverable.

Abandoned `.partial` files older than `BACKUP_PARTIAL_STALE_HOURS` (default 48) are cleaned at backup-worker startup only when the PID embedded in the filename is no longer running. Recent or active partials are left untouched.

The service runs a backup at startup by default, then repeats every 24 hours. To trigger a one-time backup without waiting for the schedule:

```bash
docker compose run --rm -e BACKUP_ONCE=true db-backup
```

## Manual restore drill

Restore only into a deliberately chosen, empty test database, never over the live application database:

```bash
createdb --host <test-db-host> --username <test-db-user> <empty-test-database>
pg_restore --host <test-db-host> --username <test-db-user> \
  --dbname <empty-test-database> --no-owner --no-privileges --exit-on-error \
  backups/<verified-archive>.dump
```

Confirm expected tables and representative records, then remove the test database when finished.

## Important limitation

Local backups protect against accidental database-level loss, but they are not offsite disaster recovery. Disk failure, theft, ransomware, or loss of the PC can destroy both the database and its local backups. Periodically copy important verified archives to a separately protected drive or another independently administered storage location.
