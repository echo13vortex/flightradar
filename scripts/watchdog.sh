#!/usr/bin/env bash
# =============================================================================
# watchdog.sh — Hlídá flightradar-api service
#
# Cron (root): */5 * * * *   (každých 5 minut)
# Setup: bash scripts/setup_crons.sh
#
# Co dělá:
#   1. Zkontroluje jestli API odpovídá na /api/summary
#   2. Pokud ne, automaticky restartuje flightradar-api service
#   3. Zapisuje do logs/watchdog.log
# =============================================================================

set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/watchdog.log"

API_URL="http://localhost:8002/api/summary"
API_PORT="8002"
SERVICE_NAME="flightradar-api"

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

# Vrací true pokud na daném portu naslouchá proces
port_listening() {
    ss -tlnp 2>/dev/null | grep -q ":${1} " || \
    ss -tlnp 2>/dev/null | grep -q ":${1}$"
}

# ── API health check ──────────────────────────────────────────────────────────
HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_URL" 2>/dev/null || echo "000")"

API_ALIVE=false
if [[ "$HTTP_CODE" != "000" ]]; then
    API_ALIVE=true
elif port_listening "$API_PORT"; then
    API_ALIVE=true
    log "WARN: Port $API_PORT aktivní, ale API nereaguje (HTTP 000)."
fi

if [[ "$API_ALIVE" == "true" ]]; then
    # Vše OK — nic nelogujeme (aby log nebyl zbytečně velký)
    exit 0
fi

# ── Restart ───────────────────────────────────────────────────────────────────
log "CHYBA: API neodpovídá (HTTP $HTTP_CODE, port $API_PORT inactive) — restartuji $SERVICE_NAME..."

systemctl restart "$SERVICE_NAME" 2>/dev/null || true
sleep 5

HTTP_CODE2="$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_URL" 2>/dev/null || echo "000")"

if [[ "$HTTP_CODE2" != "000" ]] || port_listening "$API_PORT"; then
    log "✓ $SERVICE_NAME OK po restartu (HTTP $HTTP_CODE2)."
else
    log "❌ $SERVICE_NAME stále nefunguje po restartu (HTTP $HTTP_CODE2)."
fi
