#!/usr/bin/env bash
# =============================================================================
# maintenance.sh — Noční údržba serveru FlightRadar
#
# Cron (root): 0 5 * * 0   (každou neděli v 05:00)
# Setup: bash scripts/setup_crons.sh
#
# Co dělá:
#   1. apt update + upgrade + autoremove + autoclean
#   2. SQLite integrity check + VACUUM na flightradar.db
#   3. DB size trending (log/db_trending.csv)
#   4. Zkontroluje jestli je potřeba reboot
# =============================================================================

set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
DB_FILE="$PROJECT_DIR/flightradar.db"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/maintenance.log"

mkdir -p "$LOG_DIR"

START_TS="$(date '+%Y-%m-%d %H:%M:%S')"
START_EPOCH="$(date +%s)"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

{
    echo ""
    echo "════════════════════════════════════════"
    echo "  START: Údržba systému"
    echo "  Čas:   $START_TS"
    echo "════════════════════════════════════════"
} >> "$LOG_FILE"

log "Spouštím noční údržbu serveru..."

# ── apt update ────────────────────────────────────────────────────────────────
log "apt update..."
if ! DEBIAN_FRONTEND=noninteractive apt-get update -qq >> "$LOG_FILE" 2>&1; then
    log "CHYBA: apt update selhal."
    exit 1
fi

UPGRADABLE="$(apt-get --just-print upgrade 2>/dev/null | grep '^Inst' | wc -l || echo 0)"
log "Balíků k aktualizaci: $UPGRADABLE"

# ── apt upgrade ───────────────────────────────────────────────────────────────
log "apt upgrade ($UPGRADABLE balíků)..."
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    -o Dpkg::Options::="--force-confold" \
    -o Dpkg::Options::="--force-confdef" \
    >> "$LOG_FILE" 2>&1 || true

# ── apt autoremove + autoclean ────────────────────────────────────────────────
log "apt autoremove + autoclean..."
DEBIAN_FRONTEND=noninteractive apt-get autoremove -y >> "$LOG_FILE" 2>&1 || true
apt-get autoclean -y >> "$LOG_FILE" 2>&1 || true

# ── SQLite integrity check ────────────────────────────────────────────────────
log "SQLite integrity check..."
if [[ -f "$DB_FILE" ]]; then
    RESULT=$(sqlite3 "$DB_FILE" "PRAGMA integrity_check;" 2>/dev/null | head -1 || echo "ERROR")
    if [[ "$RESULT" == "ok" ]]; then
        log "  ✓ flightradar.db: OK"
    else
        log "  ❌ flightradar.db: $RESULT"
    fi
else
    log "  PŘESKOČENO: flightradar.db neexistuje"
fi

# ── SQLite VACUUM ─────────────────────────────────────────────────────────────
log "SQLite VACUUM..."
if [[ -f "$DB_FILE" ]]; then
    BEFORE=$(stat -c%s "$DB_FILE" 2>/dev/null || echo 0)
    sqlite3 "$DB_FILE" "VACUUM;" >> "$LOG_FILE" 2>&1 || true
    AFTER=$(stat -c%s "$DB_FILE" 2>/dev/null || echo 0)
    SAVED=$(( (BEFORE - AFTER) / 1024 ))
    if [[ $SAVED -gt 0 ]]; then
        log "  flightradar.db: uvolněno ${SAVED} KB"
    else
        log "  flightradar.db: nic k uvolnění"
    fi
fi

# ── DB size trending ──────────────────────────────────────────────────────────
log "DB size trending..."
TRENDING_FILE="$LOG_DIR/db_trending.csv"
if [[ ! -f "$TRENDING_FILE" ]]; then
    echo "timestamp,flightradar_mb,prices_count,routes_count" > "$TRENDING_FILE"
fi

DB_MB=0
PRICES_COUNT=0
ROUTES_COUNT=0
if [[ -f "$DB_FILE" ]]; then
    DB_MB=$(( $(stat -c%s "$DB_FILE" 2>/dev/null || echo 0) / 1024 / 1024 ))
    PRICES_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM prices;" 2>/dev/null || echo 0)
    ROUTES_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM routes;" 2>/dev/null || echo 0)
fi
echo "$(date '+%Y-%m-%d %H:%M:%S'),${DB_MB},${PRICES_COUNT},${ROUTES_COUNT}" >> "$TRENDING_FILE"
log "  DB: ${DB_MB} MB | ${PRICES_COUNT} cen | ${ROUTES_COUNT} tras"

# ── Reboot potřeba? ───────────────────────────────────────────────────────────
REBOOT_NEEDED=false
REBOOT_MSG=""
if [[ -f /var/run/reboot-required ]]; then
    REBOOT_NEEDED=true
    if [[ -f /var/run/reboot-required.pkgs ]]; then
        PKGS="$(cat /var/run/reboot-required.pkgs | tr '\n' ' ')"
        REBOOT_MSG="⚠️  Reboot potřeba kvůli: ${PKGS}"
    else
        REBOOT_MSG="⚠️  Reboot potřeba (jádro nebo knihovny)."
    fi
    log "$REBOOT_MSG"
fi

# ── Shrnutí ───────────────────────────────────────────────────────────────────
END_EPOCH="$(date +%s)"
END_TS="$(date '+%Y-%m-%d %H:%M:%S')"
DURATION=$(( END_EPOCH - START_EPOCH ))
MINS=$(( DURATION / 60 ))
SECS=$(( DURATION % 60 ))

DISK_FREE="$(df -h / | awk 'NR==2 {print $4 " volných (" $5 " použito)"}')"

log "Hotovo za ${MINS}m ${SECS}s. Disk: $DISK_FREE. Reboot: $REBOOT_NEEDED"

{
    echo "  END: trvání=${MINS}m ${SECS}s | reboot=$REBOOT_NEEDED | disk=$DISK_FREE"
    echo "════════════════════════════════════════"
} >> "$LOG_FILE"
