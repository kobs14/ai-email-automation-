#!/usr/bin/env bash
# =============================================================================
# Backup Cleanup Script
#
# Rotates old backup files per retention policy.
#
# Environment variables:
#   PGDATABASE            - Database name (default: cleaning_email_db)
#   BACKUP_DIR            - Backup directory (default: /backups)
#   PG_RETENTION_DAYS     - Days to keep PostgreSQL backups (default: 7)
#   REDIS_RETENTION_DAYS  - Days to keep Redis backups (default: 7)
#
# Usage:
#   bash scripts/backup/backup_cleanup.sh
#
# Crontab (run weekly, Sunday 5 AM):
#   0 5 * * 0 bash /path/to/scripts/backup/backup_cleanup.sh
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PGDATABASE="${PGDATABASE:-cleaning_email_db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
PG_RETENTION_DAYS="${PG_RETENTION_DAYS:-7}"
REDIS_RETENTION_DAYS="${REDIS_RETENTION_DAYS:-7}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cleanup_files() {
    local pattern="$1"
    local retention_days="$2"
    local description="$3"
    local count=0

    log "Cleaning ${description} older than ${retention_days} days..."

    while IFS= read -r old_file; do
        rm -f "${old_file}" "${old_file}.sha256"
        count=$((count + 1))
        log "  Deleted: $(basename "${old_file}")"
    done < <(find "${BACKUP_DIR}" -name "${pattern}" -type f -mtime +"${retention_days}" 2>/dev/null)

    log "  Removed ${count} ${description} file(s)"
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
if [ ! -d "${BACKUP_DIR}" ]; then
    log "Backup directory does not exist: ${BACKUP_DIR}"
    exit 0
fi

log "Starting backup cleanup..."
log "  Backup dir: ${BACKUP_DIR}"
log "  PG retention: ${PG_RETENTION_DAYS} days"
log "  Redis retention: ${REDIS_RETENTION_DAYS} days"

# ---------------------------------------------------------------------------
# Show current state
# ---------------------------------------------------------------------------
PG_COUNT=$(find "${BACKUP_DIR}" -name "pg_${PGDATABASE}_*.dump" -type f 2>/dev/null | wc -l | tr -d ' ')
REDIS_COUNT=$(find "${BACKUP_DIR}" -name "redis_*.rdb" -type f 2>/dev/null | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)

log "Before cleanup: ${PG_COUNT} PG backups, ${REDIS_COUNT} Redis backups, ${TOTAL_SIZE} total"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
cleanup_files "pg_${PGDATABASE}_*.dump" "${PG_RETENTION_DAYS}" "PostgreSQL backups"
cleanup_files "redis_*.rdb" "${REDIS_RETENTION_DAYS}" "Redis backups"

# Also clean up orphaned checksum files (where the dump no longer exists)
log "Cleaning orphaned checksum files..."
ORPHAN_COUNT=0
while IFS= read -r sha_file; do
    base_file="${sha_file%.sha256}"
    if [ ! -f "${base_file}" ]; then
        rm -f "${sha_file}"
        ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
    fi
done < <(find "${BACKUP_DIR}" -name "*.sha256" -type f 2>/dev/null)
log "  Removed ${ORPHAN_COUNT} orphaned checksum file(s)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
PG_COUNT_AFTER=$(find "${BACKUP_DIR}" -name "pg_${PGDATABASE}_*.dump" -type f 2>/dev/null | wc -l | tr -d ' ')
REDIS_COUNT_AFTER=$(find "${BACKUP_DIR}" -name "redis_*.rdb" -type f 2>/dev/null | wc -l | tr -d ' ')
TOTAL_SIZE_AFTER=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)

log "After cleanup: ${PG_COUNT_AFTER} PG backups, ${REDIS_COUNT_AFTER} Redis backups, ${TOTAL_SIZE_AFTER} total"
log "Cleanup complete"
