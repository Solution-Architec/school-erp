#!/bin/sh
set -eu

: "${PGHOST:?PGHOST is required}"
: "${PGDATABASE:?PGDATABASE is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGPASSWORD:?PGPASSWORD is required}"

PGPORT=${PGPORT:-5432}
BACKUP_DIR=${BACKUP_DIR:-/backups}
BACKUP_PREFIX=${BACKUP_PREFIX:-school_erp}
BACKUP_INTERVAL_SECONDS=${BACKUP_INTERVAL_SECONDS:-86400}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
BACKUP_DAILY_RETENTION_DAYS=${BACKUP_DAILY_RETENTION_DAYS:-7}
BACKUP_WEEKLY_RETENTION_WEEKS=${BACKUP_WEEKLY_RETENTION_WEEKS:-4}
BACKUP_MONTHLY_RETENTION_MONTHS=${BACKUP_MONTHLY_RETENTION_MONTHS:-12}
BACKUP_S3_URI=${BACKUP_S3_URI:-}
BACKUP_RUN_ON_START=${BACKUP_RUN_ON_START:-true}
BACKUP_ONCE=${BACKUP_ONCE:-false}
VERIFY_DIR=""

case "$BACKUP_INTERVAL_SECONDS" in ''|*[!0-9]*) echo "BACKUP_INTERVAL_SECONDS must be a positive integer" >&2; exit 2 ;; esac
case "$BACKUP_PREFIX" in ""|*[!A-Za-z0-9_-]*) echo "BACKUP_PREFIX may contain only letters, digits, underscores, and hyphens" >&2; exit 2 ;; esac
case "$BACKUP_RETENTION_DAYS" in ''|*[!0-9]*) echo "BACKUP_RETENTION_DAYS must be a non-negative integer" >&2; exit 2 ;; esac
[ "$BACKUP_INTERVAL_SECONDS" -gt 0 ] || { echo "BACKUP_INTERVAL_SECONDS must be greater than zero" >&2; exit 2; }

umask 077
mkdir -p "$BACKUP_DIR"

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

write_attempt() {
  attempt_status=$1
  attempt_time=$(date -u +%Y%m%dT%H%M%SZ)
  attempt_tmp="$BACKUP_DIR/.backup-attempt.$$.tmp"
  printf '{"status":"%s","last_attempt_utc":"%s"}\n' "$attempt_status" "$attempt_time" > "$attempt_tmp"
  mv "$attempt_tmp" "$BACKUP_DIR/backup-attempt.json"
}

cleanup_verify() {
  if [ -n "$VERIFY_DIR" ]; then
    pg_ctl -D "$VERIFY_DIR/data" -m immediate -w stop >/dev/null 2>&1 || true
    rm -rf "$VERIFY_DIR"
    VERIFY_DIR=""
  fi
}
trap cleanup_verify 0
trap 'exit 1' HUP INT TERM

verify_restore() {
  archive_file=$1
  VERIFY_DIR=$(mktemp -d /tmp/pg-restore-check.XXXXXX)
  initdb -D "$VERIFY_DIR/data" --username=postgres --auth-local=trust --auth-host=trust --no-instructions >/dev/null || return 1
  pg_ctl -D "$VERIFY_DIR/data" -o "-h 127.0.0.1 -k $VERIFY_DIR -p 55432" -w start >/dev/null || return 1
  createdb -h "$VERIFY_DIR" -p 55432 -U postgres backup_restore_check || return 1
  pg_restore --host "$VERIFY_DIR" --port 55432 --username postgres \
    --dbname backup_restore_check --no-owner --no-privileges --exit-on-error "$archive_file" || return 1
  pg_ctl -D "$VERIFY_DIR/data" -m fast -w stop >/dev/null || return 1
  rm -rf "$VERIFY_DIR"
  VERIFY_DIR=""
}

run_backup() {
  timestamp=$(date -u +%Y%m%dT%H%M%SZ)
  filename="${BACKUP_PREFIX}_${timestamp}_$$_backup.dump"
  archive_file="$BACKUP_DIR/$filename"
  partial_file="$archive_file.partial"
  status_tmp="$BACKUP_DIR/.backup-status.$$.tmp"

  write_attempt "running" || return 1
  log "Starting PostgreSQL backup"
  if ! pg_dump --format=custom --compress=6 --file="$partial_file"; then
    rm -f "$partial_file"
    write_attempt "failed" || true
    log "Backup failed during pg_dump; previous verified backups were retained"
    return 1
  fi

  if ! pg_restore --list "$partial_file" >/dev/null 2>&1; then
    rm -f "$partial_file"
    write_attempt "failed" || true
    log "Backup archive validation failed; incomplete archive discarded"
    return 1
  fi

  if ! verify_restore "$partial_file"; then
    rm -f "$partial_file"
    write_attempt "failed" || true
    log "Isolated restore verification failed; archive was not published"
    return 1
  fi

  if [ -n "$BACKUP_S3_URI" ]; then
    remote_uri="${BACKUP_S3_URI%/}/$filename"
    if ! aws s3 cp "$partial_file" "$remote_uri" --sse AES256; then write_attempt "failed" || true; log "Offsite upload failed"; return 1; fi
    remote_copy=$(mktemp /tmp/remote-backup-check.XXXXXX.dump)
    if ! aws s3 cp "$remote_uri" "$remote_copy" || ! pg_restore --list "$remote_copy" >/dev/null 2>&1 || ! verify_restore "$remote_copy"; then rm -f "$remote_copy"; write_attempt "failed" || true; log "Offsite restore verification failed"; return 1; fi
    rm -f "$remote_copy"
  fi
  mv "$partial_file" "$archive_file" || { write_attempt "failed" || true; return 1; }
  size_bytes=$(wc -c < "$archive_file" | tr -d ' ')
  printf '{"status":"verified","last_success_utc":"%s","archive":"%s","size_bytes":%s,"restore_verified":true}\n' \
    "$timestamp" "$filename" "$size_bytes" > "$status_tmp" || { write_attempt "failed" || true; return 1; }
  mv "$status_tmp" "$BACKUP_DIR/backup-status.json" || { write_attempt "failed" || true; return 1; }
  write_attempt "verified" || return 1

  BACKUP_DAILY_RETENTION_DAYS="$BACKUP_DAILY_RETENTION_DAYS" BACKUP_WEEKLY_RETENTION_WEEKS="$BACKUP_WEEKLY_RETENTION_WEEKS" BACKUP_MONTHLY_RETENTION_MONTHS="$BACKUP_MONTHLY_RETENTION_MONTHS" python3 /opt/backup/backup-retention.py || return 1

  log "Backup verified and stored: $filename ($size_bytes bytes)"
}

run_cycle() {
  if run_backup; then
    return 0
  fi
  return 1
}

if [ "$BACKUP_RUN_ON_START" = "true" ] || [ "$BACKUP_ONCE" = "true" ]; then
  run_cycle || {
    [ "$BACKUP_ONCE" != "true" ] || exit 1
  }
fi

if [ "$BACKUP_ONCE" = "true" ]; then
  exit 0
fi

while :; do
  sleep "$BACKUP_INTERVAL_SECONDS"
  run_cycle || true
done
