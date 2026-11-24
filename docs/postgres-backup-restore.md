# PostgreSQL local backup and restore operations

## Local PC storage

The `db-backup` Compose service stores verified PostgreSQL backups directly in the project folder:

```text
~/school-erp/backups/
```

This is a host bind mount (`./backups:/backups`), not a Docker named volume. You can browse, copy, and archive the dump files directly from your PC. The backend mounts the same directory read-only so it can inspect backup status.

The service creates a compressed PostgreSQL 16 custom-format dump, validates it, restores it into a disposable isolated PostgreSQL instance, and publishes it only after restore verification succeeds. It then writes `backup-status.json` and applies daily, weekly, and monthly retention.

No AWS account, S3 bucket, AWS CLI, or AWS credentials are required.

## Host directory permissions

The container writes files using your Linux user and group IDs so the files remain accessible from your PC. Set these in the project-root `.env` file:

```dotenv
BACKUP_UID=1000
BACKUP_GID=1000
BACKUP_INTERVAL_SECONDS=86400
BACKUP_DAILY_RETENTION_DAYS=7
BACKUP_WEEKLY_RETENTION_WEEKS=4
BACKUP_MONTHLY_RETENTION_MONTHS=12
BACKUP_RUN_ON_START=true
BACKUP_PREFIX=school_erp
```

Replace `1000` with the output of `id -u` and `id -g` on your PC if those commands return different values. Do not put AWS keys in this configuration.

## Start and inspect

Run from the project root:

```bash
mkdir -p backups
docker compose up -d --build db-backup
docker compose logs --tail=100 db-backup
ls -lah backups
cat backups/backup-status.json
```

A successful backup has a `*_backup.dump` archive and a status file containing `"restore_verified":true`.

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
