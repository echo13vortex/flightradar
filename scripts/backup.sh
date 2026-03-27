#!/usr/bin/env bash
# =============================================================================
# backup.sh — Záloha flightradar.db na Google Drive přes rclone
#
# Cron (user): 0 3 */3 * *   (každé 3 dny ve 03:00)
# Setup:
#   sudo apt install rclone
#   rclone config  → přidat remote "gdrive" (Google Drive)
#   Pak spustit: bash scripts/setup_crons.sh
# =============================================================================

set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
DB_FILE="$PROJECT_DIR/flightradar.db"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/backup.log"
BACKUP_DIR_REMOTE="gdrive:flightradar/backups"
KEEP_BACKUPS=4

mkdir -p "$LOG_DIR"

START_TS="$(date '+%Y-%m-%d %H:%M:%S')"
START_EPOCH="$(date +%s)"
STAMP="$(date '+%Y%m%d_%H%M')"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

{ echo ""; echo "════════════════════════════════════════"; \
  echo "  BACKUP START: $START_TS"; \
  echo "════════════════════════════════════════"; } >> "$LOG_FILE"

# ── Kontrola rclone ───────────────────────────────────────────────────────────
if ! command -v rclone &>/dev/null; then
    log "CHYBA: rclone není nainstalován."
    log "Spusť: sudo apt install rclone && rclone config"
    exit 1
fi

# ── Záloha DB ─────────────────────────────────────────────────────────────────
if [[ ! -f "$DB_FILE" ]]; then
    log "CHYBA: databáze nenalezena: $DB_FILE"
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

DEST_NAME="flightradar_${STAMP}.db.gz"
DEST_TMP="$TMP_DIR/$DEST_NAME"

log "Zálohuji flightradar.db..."

# SQLite .backup = konzistentní kopie i při souběžném zápisu
if sqlite3 "$DB_FILE" ".backup '$TMP_DIR/flightradar_tmp.db'" 2>>"$LOG_FILE"; then
    gzip -c "$TMP_DIR/flightradar_tmp.db" > "$DEST_TMP"
    rm -f "$TMP_DIR/flightradar_tmp.db"
    SIZE=$(du -sh "$DEST_TMP" | cut -f1)
    log "  → $DEST_NAME ($SIZE)"
else
    log "CHYBA: sqlite3 .backup selhal"
    exit 1
fi

# ── Upload na Google Drive ─────────────────────────────────────────────────────
log "Nahrávám na Google Drive ($BACKUP_DIR_REMOTE/$STAMP/)..."
if rclone copy "$TMP_DIR/" "$BACKUP_DIR_REMOTE/$STAMP/" \
    --log-level INFO >> "$LOG_FILE" 2>&1; then
    log "Upload OK."
else
    log "CHYBA: rclone upload selhal."
    exit 1
fi

# ── Rotace starých záloh ──────────────────────────────────────────────────────
log "Rotace — zachovávám posledních $KEEP_BACKUPS záloh..."
TOTAL_DIRS=$(rclone lsf "$BACKUP_DIR_REMOTE" --dirs-only 2>/dev/null | wc -l || true)
TOTAL_DIRS=$(( ${TOTAL_DIRS:-0} + 0 ))
if [[ "$TOTAL_DIRS" -gt "$KEEP_BACKUPS" ]]; then
    DELETE_COUNT=$(( TOTAL_DIRS - KEEP_BACKUPS ))
    OLD_DIRS=$(rclone lsf "$BACKUP_DIR_REMOTE" --dirs-only 2>/dev/null \
        | sort | head -n "$DELETE_COUNT" | tr -d '/')
    for DIR in $OLD_DIRS; do
        log "  Mažu starou zálohu: $DIR"
        rclone purge "$BACKUP_DIR_REMOTE/$DIR" >> "$LOG_FILE" 2>&1 || true
    done
fi

# ── Shrnutí ───────────────────────────────────────────────────────────────────
END_EPOCH="$(date +%s)"
DURATION=$(( (END_EPOCH - START_EPOCH) / 60 ))

log "Hotovo za ${DURATION}m. → $BACKUP_DIR_REMOTE/$STAMP/"

{ echo "  END: trvání=${DURATION}m"; \
  echo "════════════════════════════════════════"; } >> "$LOG_FILE"
