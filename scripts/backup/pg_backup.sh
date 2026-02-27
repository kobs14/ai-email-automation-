#!/usr/bin/env bash
# =============================================================================
# PostgreSQL Backup Script
#
# Creates a compressed pg_dump backup in custom format (-Fc).
# Designed to run inside a Docker container on the same network as PostgreSQL.
#
# Environment variables:
#   PGHOST          - PostgreSQL host (default: postgres)
#   PGPORT          - PostgreSQL port (default: 5432)
#   PGUSER          - PostgreSQL user (default: cleaning_user)
#   PGPASSWORD      - PostgreSQL password (required)
#   PGDATABASE      - Database name (default: cleaning_email_db)
#   BACKUP_DIR      - Backup output directory (default: /backups)
#   BACKUP_RETENTION_DAYS - Days to retain local backups (default: 7)
#   UPLOAD_S3       - Set to "true" to upload to S3 (default: false)
#   AWS_S3_BUCKET   - S3 bucket name for offsite backups
#
# Usage:
#   docker compose -f docker-compose.yml -f docker-compose.backup.yml \
#     run --rm pg-backup
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
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
UPLOAD_S3="${UPLOAD_S3:-false}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/pg_${PGDATABASE}_${TIMESTAMP}.dump"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

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

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [ -z "${PGPASSWORD:-}" ]; then
    die "PGPASSWORD is not set"
fi

mkdir -p "${BACKUP_DIR}"

# Verify we can connect to PostgreSQL
log "Verifying PostgreSQL connection to ${PGHOST}:${PGPORT}/${PGDATABASE}..."
pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
    || die "Cannot connect to PostgreSQL"

# ---------------------------------------------------------------------------
# Create backup
# ---------------------------------------------------------------------------
log "Starting backup of ${PGDATABASE}..."

pg_dump \
    -h "${PGHOST}" \
    -p "${PGPORT}" \
    -U "${PGUSER}" \
    -d "${PGDATABASE}" \
    -Fc \
    --no-owner \
    --no-privileges \
    -f "${BACKUP_FILE}"

# Verify the backup file is non-empty
if [ ! -s "${BACKUP_FILE}" ]; then
    die "Backup file is empty: ${BACKUP_FILE}"
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ---------------------------------------------------------------------------
# Create checksum
# ---------------------------------------------------------------------------
sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"
log "Checksum written: ${CHECKSUM_FILE}"

# ---------------------------------------------------------------------------
# Quick verification - ensure pg_restore can read the TOC
# ---------------------------------------------------------------------------
if pg_restore --list "${BACKUP_FILE}" > /dev/null 2>&1; then
    log "Backup verification passed (TOC readable)"
else
    die "Backup verification FAILED - pg_restore cannot read the file"
fi

# ---------------------------------------------------------------------------
# Optional S3 upload
# ---------------------------------------------------------------------------
if [ "${UPLOAD_S3}" = "true" ]; then
    if [ -z "${AWS_S3_BUCKET:-}" ]; then
        log "WARNING: UPLOAD_S3=true but AWS_S3_BUCKET is not set, skipping upload"
    elif command -v aws &> /dev/null; then
        S3_KEY="backups/postgres/${PGDATABASE}/$(basename "${BACKUP_FILE}")"
        log "Uploading to s3://${AWS_S3_BUCKET}/${S3_KEY}..."
        aws s3 cp "${BACKUP_FILE}" "s3://${AWS_S3_BUCKET}/${S3_KEY}"
        aws s3 cp "${CHECKSUM_FILE}" "s3://${AWS_S3_BUCKET}/${S3_KEY}.sha256"
        log "S3 upload complete"
    else
        log "WARNING: aws CLI not found, skipping S3 upload"
    fi
fi

# ---------------------------------------------------------------------------
# Cleanup old backups
# ---------------------------------------------------------------------------
log "Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days..."
DELETED_COUNT=0
while IFS= read -r old_file; do
    rm -f "${old_file}" "${old_file}.sha256"
    DELETED_COUNT=$((DELETED_COUNT + 1))
done < <(find "${BACKUP_DIR}" -name "pg_${PGDATABASE}_*.dump" -type f -mtime +"${BACKUP_RETENTION_DAYS}" 2>/dev/null)

if [ "${DELETED_COUNT}" -gt 0 ]; then
    log "Deleted ${DELETED_COUNT} old backup(s)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL_BACKUPS=$(find "${BACKUP_DIR}" -name "pg_${PGDATABASE}_*.dump" -type f | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)
log "Backup complete. Total backups: ${TOTAL_BACKUPS}, Total size: ${TOTAL_SIZE}"
