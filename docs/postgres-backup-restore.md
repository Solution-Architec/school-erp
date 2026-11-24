# PostgreSQL backup and restore operations

## What the Compose backup service does

The `db-backup` service uses the same PostgreSQL major version as the database (PostgreSQL 16). It:

1. Creates a compressed custom-format `pg_dump` archive.
2. Checks that PostgreSQL can read the archive catalog.
3. Starts a disposable, isolated PostgreSQL instance inside the backup container and restores the archive into a temporary database with `pg_restore --exit-on-error`.
4. Publishes the archive only after the isolated restore succeeds.
5. Writes `backup-status.json`; tiered retention keeps daily, weekly and monthly recovery points. When an S3 destination is configured, the remote object is downloaded and independently restore-tested before success is reported.

The temporary restore is discarded after verification. It does not connect to or modify the live application database.

## Configuration

Set these optional values in the project-root `.env` file:

| Variable | Default | Meaning |
|---|---:|---|
| `BACKUP_INTERVAL_SECONDS` | `86400` | Interval between backup attempts (24 hours) |
| `BACKUP_DAILY_RETENTION_DAYS` | `7` | Keep the newest backup for each of the last 7 UTC days |\n| `BACKUP_WEEKLY_RETENTION_WEEKS` | `4` | Keep the newest backup for each of the last 4 ISO weeks |\n| `BACKUP_MONTHLY_RETENTION_MONTHS` | `12` | Keep the newest backup for each of the last 12 calendar months |
| `BACKUP_RUN_ON_START` | `true` | Run a backup when the service starts |
| `BACKUP_PREFIX` | `school_erp` | Prefix used for archive filenames |

The backup service reads the database name, user, and password from the existing `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` Compose settings. Do not commit secrets to Git.

## Start and inspect

```bash
docker compose up -d --build db-backup
docker compose logs --tail=100 db-backup
docker compose exec db-backup cat /backups/backup-status.json
docker compose exec db-backup ls -lh /backups
```

Backups are stored in the host-mounted `./backups` directory, separate from the PostgreSQL data volume. This lets the backend health view inspect backup state. Host loss can still destroy both database and local backup files; configure offsite storage for disaster recovery.

## Manual restore drill

For an operator-controlled restore to a separate target database, first copy an archive out of the volume:

```bash
docker compose cp db-backup:/backups/<verified-archive>.dump ./restore-test.dump
```

Then restore only into a deliberately chosen, empty test database (never the live production database):

```bash
pg_restore --host <test-db-host> --port 5432 --username <test-db-user> \
  --dbname <empty-test-database> --no-owner --no-privileges --exit-on-error \
  ./restore-test.dump
```

Confirm expected tables and representative records, then securely remove the local archive when it is no longer needed. A successful automated isolated restore proves the archive is restorable in the bundled PostgreSQL 16 environment; it does not replace periodic recovery drills against the actual production topology.

## Important production limitation

A Docker named volume is not offsite storage. Host loss, disk failure, ransomware, or deletion of the Docker volumes can destroy both the live database and its local backups. Before production use, copy verified archives to a separately administered offsite/object-storage destination with encryption, access controls, and independent retention. Offsite replication and alert delivery are not included in this phase.
