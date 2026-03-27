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

# ── 3. cron job pro denní sběr dat ───────────────────────────────────────────
info "Nastavení cron jobu (každý den ve 4:00)..."
CRON_CMD="0 4 * * * cd ${PROJECT_DIR} && ${PROJECT_DIR}/.venv/bin/python main.py >> ${PROJECT_DIR}/cron.log 2>&1"
# Přidá cron jen pokud tam ještě není
(crontab -l 2>/dev/null | grep -v "flightradar\|main.py"; echo "$CRON_CMD") | crontab -
success "Cron job nastaven (denně ve 4:00)"

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
echo "  Logy API:     sudo journalctl -u flightradar-api -f"
echo "  Logy sběru:   tail -f ${PROJECT_DIR}/cron.log"
echo "  Restart API:  sudo systemctl restart flightradar-api"
echo ""
warn "Cron sbírá data každý den ve 4:00. První sběr spusť ručně:"
echo "  source .venv/bin/activate && python main.py"
echo ""
