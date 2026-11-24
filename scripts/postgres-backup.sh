#!/bin/sh
set -eu

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_DB:=school_erp}"
: "${POSTGRES_USER:=school_erp}"
: "${BACKUP_DIR:=/backups}"
: "${BACKUP_INTERVAL_SECONDS:=86400}"
: "${BACKUP_RETENTION_DAYS:=30}"

case "$BACKUP_INTERVAL_SECONDS" in ''|*[!0-9]*) echo "BACKUP_INTERVAL_SECONDS must be an integer" >&2; exit 2 ;; esac
case "$BACKUP_RETENTION_DAYS" in ''|*[!0-9]*) echo "BACKUP_RETENTION_DAYS must be an integer" >&2; exit 2 ;; esac
[ "$BACKUP_INTERVAL_SECONDS" -ge 60 ] || { echo "BACKUP_INTERVAL_SECONDS must be at least 60" >&2; exit 2; }
[ "$BACKUP_RETENTION_DAYS" -ge 1 ] || { echo "BACKUP_RETENTION_DAYS must be at least 1" >&2; exit 2; }

mkdir -p "$BACKUP_DIR"
chmod 755 "$BACKUP_DIR"
umask 077

run_backup() {
    stamp=$(date -u +%Y%m%dT%H%M%SZ)
    file="${POSTGRES_DB}_${stamp}.dump"
    tmp="$BACKUP_DIR/.${file}.tmp"
    final="$BACKUP_DIR/$file"
    verify_db="${POSTGRES_DB}_verify_${stamp}_$$"

    echo "Starting PostgreSQL backup: $file"
    if ! pg_dump --host="$POSTGRES_HOST" --username="$POSTGRES_USER" \
        --dbname="$POSTGRES_DB" --format=custom --no-owner --no-acl --file="$tmp"; then
        rm -f "$tmp"
        echo "ERROR: pg_dump failed; no backup was published" >&2
        return 1
    fi

    if ! pg_restore --list "$tmp" >/dev/null; then
        rm -f "$tmp"
        echo "ERROR: backup archive validation failed" >&2
        return 1
    fi

    if ! createdb --host="$POSTGRES_HOST" --username="$POSTGRES_USER" "$verify_db"; then
        rm -f "$tmp"
        echo "ERROR: could not create temporary restore-verification database" >&2
        return 1
    fi

    if ! pg_restore --exit-on-error --no-owner --no-acl \
        --host="$POSTGRES_HOST" --username="$POSTGRES_USER" \
        --dbname="$verify_db" "$tmp" >/dev/null; then
        dropdb --if-exists --host="$POSTGRES_HOST" --username="$POSTGRES_USER" "$verify_db" || true
        rm -f "$tmp"
        echo "ERROR: restore verification failed; no backup was published" >&2
        return 1
    fi

    if ! dropdb --host="$POSTGRES_HOST" --username="$POSTGRES_USER" "$verify_db"; then
        rm -f "$tmp"
        echo "ERROR: temporary verification database could not be removed; backup not published" >&2
        return 1
    fi

    mv "$tmp" "$final"
    marker_tmp="$final.verified.tmp"
    printf 'restore_tested_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$marker_tmp"
    mv "$marker_tmp" "$final.verified"
    find "$BACKUP_DIR" -maxdepth 1 -type f \
        \( -name "${POSTGRES_DB}_*.dump" -o -name "${POSTGRES_DB}_*.dump.verified" \) \
        -mtime "+$BACKUP_RETENTION_DAYS" -delete
    echo "SUCCESS: $file passed archive and full temporary-database restore verification"
}

while :; do
    if ! run_backup; then
        echo "Backup attempt failed; will retry after ${BACKUP_INTERVAL_SECONDS} seconds" >&2
    fi
    sleep "$BACKUP_INTERVAL_SECONDS"
done
