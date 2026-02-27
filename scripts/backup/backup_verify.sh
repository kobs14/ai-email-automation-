#!/usr/bin/env bash
# =============================================================================
# Backup Verification Script
#
# Checks that the latest backup exists, is recent, and is readable.
# Sends a Telegram alert on failure.
#
# Environment variables:
#   PGDATABASE            - Database name (default: cleaning_email_db)
#   BACKUP_DIR            - Backup directory (default: /backups)
#   MAX_AGE_HOURS         - Maximum allowed backup age (default: 2)
#   TELEGRAM_BOT_TOKEN    - Telegram bot token for alerts (optional)
#   TELEGRAM_ADMIN_CHAT_ID - Telegram chat ID for alerts (optional)
#
# Usage:
#   bash scripts/backup/backup_verify.sh
#
# Crontab (run daily at 4 AM):
#   0 4 * * * bash /path/to/scripts/backup/backup_verify.sh
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PGDATABASE="${PGDATABASE:-cleaning_email_db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-2}"
HOSTNAME_STR=$(hostname 2>/dev/null || echo "unknown")

ERRORS=()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

add_error() {
    ERRORS+=("$1")
    log "FAIL: $1"
}

send_telegram_alert() {
    local message="$1"

    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_ADMIN_CHAT_ID:-}" ]; then
        log "Telegram not configured, skipping alert"
        return
    fi

    local text
    text=$(printf "🚨 Backup Verification FAILED\n\nHost: %s\nDatabase: %s\nTime: %s\n\nErrors:\n%s" \
        "${HOSTNAME_STR}" "${PGDATABASE}" "$(date '+%Y-%m-%d %H:%M:%S')" "${message}")

    curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_ADMIN_CHAT_ID}" \
        -d text="${text}" \
        -d parse_mode="HTML" \
        > /dev/null 2>&1 \
        && log "Telegram alert sent" \
        || log "WARNING: Failed to send Telegram alert"
}

# ---------------------------------------------------------------------------
# Check 1: Backup file exists
# ---------------------------------------------------------------------------
log "Checking for latest backup..."
LATEST_BACKUP=$(find "${BACKUP_DIR}" -name "pg_${PGDATABASE}_*.dump" -type f 2>/dev/null \
    | sort -r | head -n1)

if [ -z "${LATEST_BACKUP}" ]; then
    add_error "No backup files found in ${BACKUP_DIR}"
else
    log "Latest backup: ${LATEST_BACKUP}"

    # ---------------------------------------------------------------------------
    # Check 2: Backup age
    # ---------------------------------------------------------------------------
    log "Checking backup age (max ${MAX_AGE_HOURS} hours)..."
    BACKUP_AGE_SECONDS=$(( $(date +%s) - $(stat -c %Y "${LATEST_BACKUP}" 2>/dev/null || stat -f %m "${LATEST_BACKUP}" 2>/dev/null) ))
    BACKUP_AGE_HOURS=$(( BACKUP_AGE_SECONDS / 3600 ))

    if [ "${BACKUP_AGE_HOURS}" -gt "${MAX_AGE_HOURS}" ]; then
        add_error "Backup is ${BACKUP_AGE_HOURS} hours old (max: ${MAX_AGE_HOURS})"
    else
        log "PASS: Backup is ${BACKUP_AGE_HOURS} hours old"
    fi

    # ---------------------------------------------------------------------------
    # Check 3: File is non-empty
    # ---------------------------------------------------------------------------
    log "Checking backup is non-empty..."
    if [ ! -s "${LATEST_BACKUP}" ]; then
        add_error "Backup file is empty: ${LATEST_BACKUP}"
    else
        BACKUP_SIZE=$(du -h "${LATEST_BACKUP}" | cut -f1)
        log "PASS: Backup size is ${BACKUP_SIZE}"
    fi

    # ---------------------------------------------------------------------------
    # Check 4: Checksum verification
    # ---------------------------------------------------------------------------
    CHECKSUM_FILE="${LATEST_BACKUP}.sha256"
    log "Checking checksum..."
    if [ -f "${CHECKSUM_FILE}" ]; then
        if sha256sum --check "${CHECKSUM_FILE}" --quiet 2>/dev/null; then
            log "PASS: Checksum matches"
        else
            add_error "Checksum verification failed for ${LATEST_BACKUP}"
        fi
    else
        add_error "No checksum file found: ${CHECKSUM_FILE}"
    fi

    # ---------------------------------------------------------------------------
    # Check 5: pg_restore can read the backup
    # ---------------------------------------------------------------------------
    log "Checking backup readability..."
    if command -v pg_restore &> /dev/null; then
        if pg_restore --list "${LATEST_BACKUP}" > /dev/null 2>&1; then
            TABLE_COUNT=$(pg_restore --list "${LATEST_BACKUP}" 2>/dev/null | grep -c "TABLE " || true)
            log "PASS: Backup is readable (${TABLE_COUNT} tables)"
        else
            add_error "pg_restore cannot read backup: ${LATEST_BACKUP}"
        fi
    else
        log "SKIP: pg_restore not available, cannot check readability"
    fi
fi

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
if [ ${#ERRORS[@]} -eq 0 ]; then
    log "All verification checks PASSED"
    exit 0
else
    log "Verification FAILED with ${#ERRORS[@]} error(s):"
    ERROR_MSG=""
    for err in "${ERRORS[@]}"; do
        log "  - ${err}"
        ERROR_MSG="${ERROR_MSG}- ${err}\n"
    done

    send_telegram_alert "${ERROR_MSG}"
    exit 1
fi
