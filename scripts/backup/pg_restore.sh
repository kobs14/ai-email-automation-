#!/usr/bin/env bash
# =============================================================================
# PostgreSQL Restore Script
#
# Restores a database from a pg_dump custom-format backup.
# Includes checksum verification and safety prompts.
#
# Environment variables:
#   PGHOST      - PostgreSQL host (default: postgres)
#   PGPORT      - PostgreSQL port (default: 5432)
#   PGUSER      - PostgreSQL superuser (default: cleaning_user)
#   PGPASSWORD  - PostgreSQL password (required)
#   PGDATABASE  - Database name (default: cleaning_email_db)
#   BACKUP_DIR  - Backup directory (default: /backups)
#
# Usage:
#   # Restore the latest backup
#   ./pg_restore.sh --latest
#
#   # Restore a specific backup
#   ./pg_restore.sh /backups/pg_cleaning_email_db_20240115_120000.dump
#
#   # Verify only (no changes)
#   ./pg_restore.sh --verify-only --latest
#   ./pg_restore.sh --verify-only /path/to/backup.dump
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PGHOST="${PGHOST:-postgres}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-cleaning_user}"
PGDATABASE="${PGDATABASE:-cleaning_email_db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

VERIFY_ONLY=false
BACKUP_FILE=""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

die() {
    log "ERROR: $*" >&2
    exit 1
}

usage() {
    echo "Usage: $0 [--verify-only] [--latest | <backup-file>]"
    echo ""
    echo "Options:"
    echo "  --latest       Use the most recent backup file"
    echo "  --verify-only  Check backup integrity without restoring"
    echo "  <backup-file>  Path to a specific backup file"
    exit 1
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
        --latest)
            BACKUP_FILE=$(find "${BACKUP_DIR}" -name "pg_${PGDATABASE}_*.dump" -type f 2>/dev/null \
                | sort -r | head -n1)
            if [ -z "${BACKUP_FILE}" ]; then
                die "No backup files found in ${BACKUP_DIR}"
            fi
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

if [ -z "${BACKUP_FILE}" ]; then
    usage
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    die "Backup file not found: ${BACKUP_FILE}"
fi

if [ ! -s "${BACKUP_FILE}" ]; then
    die "Backup file is empty: ${BACKUP_FILE}"
fi

if [ -z "${PGPASSWORD:-}" ]; then
    die "PGPASSWORD is not set"
fi

# ---------------------------------------------------------------------------
# Verify checksum
# ---------------------------------------------------------------------------
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
    log "Verifying checksum..."
    if sha256sum --check "${CHECKSUM_FILE}" --quiet 2>/dev/null; then
        log "Checksum verification PASSED"
    else
        die "Checksum verification FAILED - backup may be corrupted"
    fi
else
    log "WARNING: No checksum file found at ${CHECKSUM_FILE}, skipping verification"
fi

# ---------------------------------------------------------------------------
# Verify backup is readable
# ---------------------------------------------------------------------------
log "Verifying backup format..."
if pg_restore --list "${BACKUP_FILE}" > /dev/null 2>&1; then
    TABLE_COUNT=$(pg_restore --list "${BACKUP_FILE}" 2>/dev/null | grep -c "TABLE " || true)
    log "Backup is valid (${TABLE_COUNT} tables found)"
else
    die "Backup file is unreadable by pg_restore"
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
BACKUP_DATE=$(stat -c %y "${BACKUP_FILE}" 2>/dev/null || stat -f %Sm "${BACKUP_FILE}" 2>/dev/null)
log "Backup file: ${BACKUP_FILE}"
log "Backup size: ${BACKUP_SIZE}"
log "Backup date: ${BACKUP_DATE}"

# ---------------------------------------------------------------------------
# Verify-only mode stops here
# ---------------------------------------------------------------------------
if [ "${VERIFY_ONLY}" = true ]; then
    log "Verify-only mode: backup is valid. No changes made."
    exit 0
fi

# ---------------------------------------------------------------------------
# Safety confirmation
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================"
echo "  WARNING: This will DROP and RECREATE the database '${PGDATABASE}'"
echo "  on ${PGHOST}:${PGPORT}"
echo ""
echo "  ALL EXISTING DATA WILL BE LOST."
echo ""
echo "  Restoring from: ${BACKUP_FILE}"
echo "======================================================================"
echo ""
read -rp "Type 'YES' to proceed: " CONFIRM

if [ "${CONFIRM}" != "YES" ]; then
    log "Restore cancelled by user"
    exit 0
fi

# ---------------------------------------------------------------------------
# Stop application services (best-effort)
# ---------------------------------------------------------------------------
log "Stopping application services..."
if command -v docker &> /dev/null; then
    for svc in cleaning_email_celery_worker cleaning_email_celery_beat cleaning_email_telegram_bot cleaning_email_backend; do
        docker stop "${svc}" 2>/dev/null && log "  Stopped ${svc}" || true
    done
else
    log "  Docker not available, skipping service stop (ensure services are stopped manually)"
fi

# ---------------------------------------------------------------------------
# Drop and recreate database
# ---------------------------------------------------------------------------
log "Dropping database ${PGDATABASE}..."
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PGDATABASE}' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${PGDATABASE};"

log "Creating database ${PGDATABASE}..."
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -c "CREATE DATABASE ${PGDATABASE};"

# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
log "Restoring backup..."
pg_restore \
    -h "${PGHOST}" \
    -p "${PGPORT}" \
    -U "${PGUSER}" \
    -d "${PGDATABASE}" \
    --no-owner \
    --no-privileges \
    --exit-on-error \
    "${BACKUP_FILE}"

log "Restore complete"

# ---------------------------------------------------------------------------
# Verify restore
# ---------------------------------------------------------------------------
log "Verifying restored database..."
TABLE_COUNT=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -t \
    -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" \
    | tr -d ' ')
log "Restored database has ${TABLE_COUNT} tables"

# ---------------------------------------------------------------------------
# Restart application services (best-effort)
# ---------------------------------------------------------------------------
log "Restarting application services..."
if command -v docker &> /dev/null; then
    for svc in cleaning_email_celery_worker cleaning_email_celery_beat cleaning_email_telegram_bot cleaning_email_backend; do
        docker start "${svc}" 2>/dev/null && log "  Started ${svc}" || true
    done
else
    log "  Docker not available, restart services manually"
fi

log "Restore complete. Database '${PGDATABASE}' has been restored from ${BACKUP_FILE}"
