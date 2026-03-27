# ✈️ FlightRadar

Automatizovaný tracker cen letenek z **Prahy (PRG)** do vybraných destinací.
Data se sbírají 1× denně pomocí headless scraperu, ukládají do SQLite a zobrazují v přehledném webovém dashboardu.

---

## Sledované destinace

| Destinace | IATA | Přestupy | Směry |
|-----------|------|----------|-------|
| 🇯🇵 Japonsko – Tokio | NRT | Ano (Doha / Dubaj) | PRG→NRT + NRT→PRG |
| 🇯🇵 Okinawa – Naha | OKA | Ano (Tokio + domácí) | PRG→OKA + OKA→PRG |
| 🇵🇹 Madeira – Funchal | FNC | Možné | PRG→FNC + FNC→PRG |
| 🇵🇹 Lisabon | LIS | Ne (pouze přímé) | PRG→LIS + LIS→PRG |

Hledají se lety na **prodloužené víkendy** (čtvrtek + pátek odlet tam, neděle + pondělí odlet zpět). Každý směr je zobrazeno zvlášť, takže si můžeš zkombinovat nejlevnější termíny.

---

## Tech stack

| Vrstva | Technologie |
|--------|-------------|
| Scraping | Python 3.10+, Playwright (headless Chromium), Requests |
| Databáze | SQLite via SQLAlchemy |
| Backend API | FastAPI + Uvicorn (port 8002) |
| Frontend | React 18 + Recharts + Vite |

---

## Architektura

```
[Cron job – 1× denně]
        ↓
[main.py – spouštěč sběru]
  ├── scrapers/kiwi.py       → Playwright scraping Kiwi.com (GraphQL intercept)
  ├── scrapers/travelpayouts.py → Travelpayouts / Aviasales Data API
  ├── scrapers/wizzair.py    → Wizzair neoficiální API (neaktivní – vrací 404)
  └── scrapers/amadeus.py    → Amadeus API (neaktivní – AMADEUS_ENABLED=False)
        ↓
[normalizer.py – převod měn na EUR]
        ↓
[SQLite databáze – flightradar.db]
        ↓
[FastAPI backend – REST API na portu 8002]
        ↓
[React frontend – dashboard na portu 5173 (dev) / 80 (produkce)]
```

---

## Instalace

### Požadavky

- Ubuntu 22.04+ (nebo Raspberry Pi OS 64-bit / Ubuntu Server)
- Python 3.10+
- Node.js 18+
- ~500 MB místa (Chromium)

### Rychlá instalace (doporučeno)

```bash
git clone https://github.com/echo13vortex/flightradar.git
cd flightradar
bash install.sh
```

Skript automaticky:
1. Nainstaluje systémové závislosti (`apt`)
2. Nainstaluje Node.js 20 (pokud chybí)
3. Vytvoří Python virtual environment (`.venv`)
4. Nainstaluje Python balíčky (`requirements.txt`)
5. Stáhne a nainstaluje headless Chromium pro Playwright
6. Sestaví React frontend (`frontend/dist/`)
7. Vytvoří `.env` soubor ze šablony

### Ruční instalace

```bash
git clone https://github.com/echo13vortex/flightradar.git
cd flightradar

# Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Playwright + Chromium (~200 MB)
playwright install chromium --with-deps

# Frontend
cd frontend && npm install && npm run build && cd ..

# Konfigurace
cp .env.example .env
nano .env   # doplň TRAVELPAYOUTS_TOKEN
```

---

## Konfigurace (.env)

```env
# Travelpayouts / Aviasales Data API (zdarma, registrace na travelpayouts.com)
TRAVELPAYOUTS_TOKEN=tvůj_token

# Port backendu (default: 8002)
PORT=8002

# Databáze (default: SQLite v adresáři projektu)
DATABASE_URL=sqlite:///flightradar.db

# Úroveň logování
LOG_LEVEL=INFO
```

**Travelpayouts token** získáš zdarma na [travelpayouts.com](https://travelpayouts.com) → API → Data API. Funguje bez tokenu, ale s tokenem máš vyšší limity.

---

## Spuštění (vývojové prostředí)

```bash
# Spustí backend i frontend v jednom okně (Ctrl+C ukončí obojí)
bash start.sh
# → http://localhost:5173
```

Nebo odděleně:

```bash
# Backend
source .venv/bin/activate
uvicorn api.app:app --reload --port 8002 --app-dir .

# Frontend (druhý terminál)
cd frontend && npm run dev
```

---

## Sběr dat

```bash
source .venv/bin/activate

# Všechny destinace
python main.py

# Jen jedna destinace
python main.py --dest LIS
python main.py --dest FNC
python main.py --dest OKA
python main.py --dest NRT
```

Sběr trvá dle destinace:
- **LIS** – ~3 minuty (13 dat × 2 směry)
- **FNC** – ~7 minut (25 dat × 2 směry)
- **OKA** – ~25 minut (52 dat × 2 směry)
- **NRT** – ~25 minut (52 dat × 2 směry)

---

## Produkční nasazení (nginx + systemd)

Pro trvalý provoz na Raspberry Pi / Ubuntu serveru:

```bash
bash setup-production.sh
```

Skript nakonfiguruje:
- **nginx** na portu 80 – servíruje frontend + proxuje `/api/`
- **systemd service** `flightradar-api` – uvicorn běží na pozadí a startuje při restartu
- **cron job** – `python main.py` každý den ve 4:00

Po instalaci je dashboard dostupný na `http://<IP-adresy-pi>`.

### Užitečné příkazy

```bash
# Stav API služby
sudo systemctl status flightradar-api

# Logy API v reálném čase
sudo journalctl -u flightradar-api -f

# Restart API
sudo systemctl restart flightradar-api

# Logy cron sběru
tail -f cron.log

# Ruční spuštění sběru
source .venv/bin/activate && python main.py
```

---

## API endpointy

Backend běží na portu 8002. Swagger dokumentace: `http://localhost:8002/docs`

| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | `/api/destinations` | Seznam destinací s konfigurací |
| GET | `/api/summary` | Nejlevnější aktuální ceny (všechny destinace) |
| GET | `/api/prices/{iata}` | Lety pro destinaci (s filtrováním, řazením) |
| GET | `/api/prices/{iata}/stats` | Statistiky (min / průměr / max) |
| GET | `/api/prices/{iata}/chart` | Data pro graf vývoje cen |
| GET | `/api/snapshots` | Historie sběrů (monitoring) |

Parametry pro `/api/prices/{iata}`:
- `?days=30` – pouze lety v nejbližších N dnech
- `?limit=100` – maximálně N výsledků

---

## Databázový model

### `routes` – sledované trasy
```
id, origin_iata, destination_iata, destination_name, airline, active, created_at
```

### `prices` – nasbírané ceny
```
id, route_id, price_eur, price_original, currency_original,
departure_date, return_date, airline_detail, flight_numbers,
stops, duration_minutes, departure_time, arrival_time,
source_url, collected_at
```

### `snapshots` – metadata sběrů
```
id, collected_at, source, route, status, records_saved, error_message
```

---

## Struktura projektu

```
flightradar/
├── config.py              # Destinace, parametry hledání, helper funkce
├── database.py            # SQLAlchemy modely + init_db() + save_prices()
├── normalizer.py          # Převod měn na EUR
├── main.py                # Spouštěč sběru (argparse: --dest, --airline)
├── scrapers/
│   ├── kiwi.py            # ★ Hlavní scraper – Playwright + GraphQL intercept
│   ├── travelpayouts.py   # Travelpayouts / Aviasales Data API
│   ├── ryanair.py         # Ryanair (neaktivní – z PRG sem nelétá)
│   ├── wizzair.py         # Wizzair (neaktivní – API vrací 404)
│   └── amadeus.py         # Amadeus API (neaktivní – AMADEUS_ENABLED=False)
├── api/
│   └── app.py             # FastAPI REST API
├── frontend/
│   ├── vite.config.js     # Vite + proxy /api → port 8002
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── Header.jsx         # Hlavička
│           ├── Summary.jsx        # Karty destinací
│           ├── RouteDetail.jsx    # Detail destinace (tabulka + graf)
│           ├── PriceChart.jsx     # Graf vývoje nejnižší ceny
│           ├── PriceTable.jsx     # Tabulka letů (řaditelná, odkaz na Kiwi)
│           └── SnapshotLog.jsx    # Log sběrů
├── install.sh             # Instalace pro Ubuntu / Raspberry Pi
├── setup-production.sh    # Produkce: nginx + systemd + cron
├── start.sh               # Dev spuštění (backend + frontend najednou)
├── requirements.txt       # Python závislosti
├── .env.example           # Šablona konfigurace
└── .gitignore
```

---

## Jak funguje scraping

Hlavní zdroj dat je **Kiwi.com** bez API klíče:

1. Playwright spustí headless Chromium
2. Načte `kiwi.com/search/results/{origin}/{destination}/{datum}/no-return/`
3. Zachytí GraphQL odpověď na `SearchOneWayItinerariesQuery`
4. Parsuje ceny, aerolinky, časy odletu/příletu, přestupy
5. Uloží do SQLite s deduplication (nezapíše duplicitní záznamy)

> **Poznámka ke slugům:** URL slug destinace musí přesně odpovídat Kiwi interním názvům.
> Špatný slug → Kiwi vrátí zpáteční query místo jednosměrné.
> Správné slugy: `prague-czechia`, `lisbon-portugal`, `funchal-portugal`, `tokyo-japan`, `naha-okinawa-island-japan`

---

## Licence

Osobní projekt, není určen pro komerční využití.
