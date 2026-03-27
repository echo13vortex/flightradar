#!/usr/bin/env bash
# =============================================================================
# setup_crons.sh — Nastaví VŠECHNY cron joby FlightRadar
#
# Spouštět jako root: sudo bash scripts/setup_crons.sh
# =============================================================================

set -e

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

# Zjisti uživatele projektu (vlastník PROJECT_DIR)
PROJECT_USER="$(stat -c '%U' "$PROJECT_DIR")"

mkdir -p "$LOG_DIR"
chown "$PROJECT_USER":"$PROJECT_USER" "$LOG_DIR"

# ── Spustitelnost skriptů ─────────────────────────────────────────────────────
chmod +x \
    "$SCRIPTS_DIR/backup.sh" \
    "$SCRIPTS_DIR/maintenance.sh" \
    "$SCRIPTS_DIR/watchdog.sh"

# ── Logrotate ─────────────────────────────────────────────────────────────────
cat > /etc/logrotate.d/flightradar <<EOF
$LOG_DIR/*.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
    create 0640 $PROJECT_USER $PROJECT_USER
}
EOF
echo "  ✓ Logrotate nainstalován (/etc/logrotate.d/flightradar)"

# ── Unattended security upgrades ─────────────────────────────────────────────
if ! dpkg -l unattended-upgrades &>/dev/null 2>&1; then
    apt-get install -y unattended-upgrades > /dev/null 2>&1
fi
cat > /etc/apt/apt.conf.d/50unattended-upgrades-flightradar <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
cat > /etc/apt/apt.conf.d/20auto-upgrades-flightradar <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
echo "  ✓ Unattended security upgrades zapnuty"

# ── Root crontab (watchdog + maintenance) ────────────────────────────────────
ROOT_EXISTING=$(crontab -l 2>/dev/null | grep -v "flightradar" | grep -v "watchdog\|maintenance" || true)

ROOT_CRONS=$(cat <<EOF

# ── FlightRadar monitoring ────────────────────────────────────────────────────
# Watchdog (API health + auto-restart) — každých 5 minut
*/5 * * * *  $SCRIPTS_DIR/watchdog.sh >> $LOG_DIR/watchdog.log 2>&1

# Noční systémová údržba — každou neděli v 05:00
0 5 * * 0    $SCRIPTS_DIR/maintenance.sh >> $LOG_DIR/maintenance.log 2>&1
EOF
)

(echo "$ROOT_EXISTING"; echo "$ROOT_CRONS") | crontab -
echo "  ✓ Root crontab: watchdog (*/5 min) + maintenance (Ne 05:00)"

# ── User crontab (sběr dat + záloha) ─────────────────────────────────────────
USER_EXISTING=$(crontab -u "$PROJECT_USER" -l 2>/dev/null | grep -v "flightradar\|main.py\|backup" || true)

USER_CRONS=$(cat <<EOF

# ── FlightRadar data ──────────────────────────────────────────────────────────
# Sběr dat — každý den ve 04:00
0 4 * * *    cd $PROJECT_DIR && $VENV_PYTHON main.py >> $LOG_DIR/cron.log 2>&1

# Záloha DB na Google Drive — každé 3 dny ve 03:00
# (vyžaduje: sudo apt install rclone && rclone config)
0 3 */3 * *  $SCRIPTS_DIR/backup.sh >> $LOG_DIR/backup.log 2>&1
EOF
)

(echo "$USER_EXISTING"; echo "$USER_CRONS") | crontab -u "$PROJECT_USER" -
echo "  ✓ User ($PROJECT_USER) crontab: sběr dat (04:00) + záloha (každé 3 dny 03:00)"

# ── Shrnutí ───────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✓ FlightRadar — všechny cron joby nastaveny"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  SBĚR DAT:"
echo "    Lety           04:00 (denně)"
echo ""
echo "  MONITORING:"
echo "    Watchdog       každých 5 min (auto-restart API)"
echo ""
echo "  ÚDRŽBA:"
echo "    Systém         Ne 05:00 (týdně)"
echo "    Záloha DB      03:00 každé 3 dny (Google Drive)"
echo ""
echo "  BEZPEČNOST:"
echo "    Unattended security upgrades: ZAPNUTy"
echo "    Logrotate: /etc/logrotate.d/flightradar"
echo ""
echo "  Ruční test watchdogu:  sudo bash $SCRIPTS_DIR/watchdog.sh"
echo "  Ruční záloha:          bash $SCRIPTS_DIR/backup.sh"
echo "  Ruční údržba:          sudo bash $SCRIPTS_DIR/maintenance.sh"
echo ""
echo "  ⚠️  Google Drive zálohy vyžadují:"
echo "    1. sudo apt install rclone"
echo "    2. rclone config  (přidat remote 'gdrive')"
echo "════════════════════════════════════════════════════════════"
