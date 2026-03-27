#!/usr/bin/env bash
# Spustí backend (uvicorn) a frontend (vite) zároveň.
# Použití: ./start.sh
# Ukončení: Ctrl+C zastaví oba procesy.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Barvy pro přehlednost
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RESET='\033[0m'

echo -e "${CYAN}▶  Spouštím FlightRadar...${RESET}"
echo -e "   Backend  → http://localhost:8002/docs"
echo -e "   Frontend → http://localhost:5173"
echo ""

# Cleanup – při Ctrl+C zastaví oba procesy
cleanup() {
    echo -e "\n${CYAN}■  Ukončuji procesy...${RESET}"
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    echo "Hotovo."
}
trap cleanup INT TERM

# Backend
source "$ROOT/.venv/bin/activate"
uvicorn api.app:app --reload --port 8002 --app-dir "$ROOT" 2>&1 | sed "s/^/${GREEN}[backend]${RESET} /" &
BACKEND_PID=$!

# Počkej sekundu, ať backend nabíhá první
sleep 1

# Frontend
cd "$ROOT/frontend"
npm run dev 2>&1 | sed "s/^/${CYAN}[frontend]${RESET} /" &
FRONTEND_PID=$!

# Otevři prohlížeč
sleep 2
open http://localhost:5173

# Čekej dokud nezmáčkneš Ctrl+C
wait "$BACKEND_PID" "$FRONTEND_PID"
