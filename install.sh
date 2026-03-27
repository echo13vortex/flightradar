#!/bin/bash
# FlightRadar – instalační skript pro Ubuntu Server (včetně Raspberry Pi 3/4)
# Použití: bash install.sh
# Spouštět z adresáře projektu.

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${CYAN}▶  $1${NC}"; }
success() { echo -e "${GREEN}✓  $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $1${NC}"; }
error()   { echo -e "${RED}✗  $1${NC}"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         FlightRadar – instalace          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Systémové balíčky ──────────────────────────────────────────────────────
info "Aktualizace systému a instalace závislostí..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libxkbcommon0 libasound2
success "Systémové balíčky nainstalovány"

# ── 2. Node.js (pro build frontendu) ─────────────────────────────────────────
if ! command -v node &> /dev/null; then
    info "Instalace Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - -qq
    sudo apt-get install -y -qq nodejs
    success "Node.js $(node --version) nainstalován"
else
    success "Node.js $(node --version) již nainstalován"
fi

# ── 3. Python venv ────────────────────────────────────────────────────────────
info "Vytváření Python virtual environment (.venv)..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
success "Virtual environment připraven"

# ── 4. Python závislosti ──────────────────────────────────────────────────────
info "Instalace Python balíčků (requirements.txt)..."
pip install -r requirements.txt -q
success "Python balíčky nainstalovány"

# ── 5. Playwright + Chromium ──────────────────────────────────────────────────
info "Instalace headless Chromium pro Playwright..."
warn "Toto může trvat několik minut (stahování ~200 MB)..."
playwright install chromium --with-deps
success "Playwright Chromium nainstalován"

# ── 6. Frontend (npm + build) ─────────────────────────────────────────────────
info "Instalace npm balíčků a build frontendu..."
cd frontend
npm install --silent
npm run build --silent
cd ..
success "Frontend sestavен → frontend/dist/"

# ── 7. .env soubor ────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    warn ".env soubor vytvořen z šablony – doplň TRAVELPAYOUTS_TOKEN pokud máš"
else
    success ".env soubor již existuje"
fi

# ── Hotovo ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Instalace dokončena! ✈           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Další kroky:"
echo "  1. Spusť první sběr dat:   source .venv/bin/activate && python main.py"
echo "  2. Spusť aplikaci:         bash start.sh"
echo "  3. Pro produkci (nginx):   bash setup-production.sh"
echo ""
echo "  (volitelně) Přidej Travelpayouts token do .env: TRAVELPAYOUTS_TOKEN=..."
echo ""
