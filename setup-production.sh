#!/bin/bash
# FlightRadar – produkční nasazení (nginx + systemd)
# Spouštět po install.sh. Vyžaduje sudo.
# Použití: bash setup-production.sh

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${CYAN}▶  $1${NC}"; }
success() { echo -e "${GREEN}✓  $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER="$(whoami)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    FlightRadar – produkční nasazení      ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Adresář projektu: $PROJECT_DIR"
echo "Uživatel:         $USER"
echo ""

# ── 1. nginx ─────────────────────────────────────────────────────────────────
info "Instalace nginx..."
sudo apt-get install -y -qq nginx
success "nginx nainstalován"

info "Konfigurace nginx..."
sudo tee /etc/nginx/sites-available/flightradar > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Statický frontend (React build)
    root ${PROJECT_DIR}/frontend/dist;
    index index.html;

    # SPA fallback – všechny routes vrátí index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy → uvicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/flightradar /etc/nginx/sites-enabled/flightradar
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
success "nginx nakonfigurován a spuštěn"

# ── 2. systemd service pro API ────────────────────────────────────────────────
info "Vytváření systemd service pro FlightRadar API..."
sudo tee /etc/systemd/system/flightradar-api.service > /dev/null <<EOF
[Unit]
Description=FlightRadar API (FastAPI + uvicorn)
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/uvicorn api.app:app --host 127.0.0.1 --port 8002 --app-dir ${PROJECT_DIR}
Restart=always
RestartSec=5
Environment=PYTHONPATH=${PROJECT_DIR}

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable flightradar-api
sudo systemctl restart flightradar-api
success "flightradar-api service spuštěn"

# ── 3. Cron joby + watchdog + maintenance + logrotate ────────────────────────
info "Nastavení cron jobů, watchdogu a logrotate..."
chmod +x "${PROJECT_DIR}/scripts/"*.sh
bash "${PROJECT_DIR}/scripts/setup_crons.sh"
success "Cron joby nastaveny"

# ── Hotovo ────────────────────────────────────────────────────────────────────
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Produkce spuštěna! ✈               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  Dashboard:    http://${IP}"
echo "  API:          http://${IP}/api/summary"
echo ""
echo "  Logy API:      sudo journalctl -u flightradar-api -f"
echo "  Logy sběru:    tail -f ${PROJECT_DIR}/logs/cron.log"
echo "  Logy watchdog: tail -f ${PROJECT_DIR}/logs/watchdog.log"
echo "  Restart API:   sudo systemctl restart flightradar-api"
echo "  Ruční záloha:  bash ${PROJECT_DIR}/scripts/backup.sh"
echo ""
warn "První sběr dat spusť ručně (cron začne automaticky ve 04:00):"
echo "  source .venv/bin/activate && python main.py"
echo ""
