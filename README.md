# ✈️ FlightRadar

Automatizovaný tracker cen letenek z **Prahy (PRG)** do vybraných destinací.
Data se sbírají 1× denně, ukládají do databáze a zobrazují v přehledném webovém dashboardu s grafy.

---

## Sledované destinace

| Destinace | IATA | Přestupy | Zdroje dat |
|-----------|------|----------|------------|
| 🇯🇵 Japonsko – Tokio | NRT | Ano (Doha / Dubaj) | Qatar Airways, Emirates |
| 🇯🇵 Okinawa – Naha | OKA | Ano (Tokio + domácí) | Qatar Airways, Emirates |
| 🇵🇹 Madeira – Funchal | FNC | Případně | Ryanair, Wizzair, Qatar, Emirates |
| 🇵🇹 Lisabon | LIS | Případně | Ryanair, Wizzair, Qatar, Emirates |

---

## Architektura

```
[Cron job – 1× denně]
        ↓
[Python scrapery]
  ├── ryanair.py    → ryanair-py (neoficiální)
  ├── wizzair.py    → Wizzair community endpointy
  └── amadeus.py    → Amadeus API (Qatar Airways + Emirates)
        ↓
[normalizer.py – převod měn na EUR]
        ↓
[SQLite / PostgreSQL databáze]
        ↓
[FastAPI backend – REST API]
        ↓
[React frontend – grafy + přehled cen]
```

---

## Tech stack

| Vrstva | Technologie |
|--------|-------------|
| Sběr dat | Python 3.11+, `ryanair-py`, `amadeus`, `requests` |
| Databáze | SQLite (lokálně) / PostgreSQL (VPS) via SQLAlchemy |
| Backend API | FastAPI + Uvicorn |
| Frontend | React 18 + Recharts + Vite |
| Nasazení | VPS cron job / Cloudflare Pages |

---

## Instalace a spuštění

### Požadavky

- Python 3.11+
- Node.js 18+
- Amadeus API klíče (zdarma na [developers.amadeus.com](https://developers.amadeus.com))

### 1. Klonování a nastavení

```bash
git clone https://github.com/<tvuj-ucet>/flightradar.git
cd flightradar

# Python závislosti
pip install -r requirements.txt

# Konfigurace
cp .env.example .env
# → vyplň AMADEUS_API_KEY a AMADEUS_API_SECRET v .env
```

### 2. Inicializace databáze

```bash
python database.py --init
```

Vytvoří `flightradar.db` a naplní tabulku tras z `config.py`.

### 3. První sběr dat

```bash
# Dry-run – jen zobrazí co by sbíralo, nic neuloží
python main.py --dry-run

# Ostrý sběr – všechny trasy
python main.py

# Jen jedna aerolinka
python main.py --airline amadeus

# Jen jedna destinace
python main.py --dest LIS
```

### 4. Backend API

```bash
uvicorn api.app:app --reload --port 8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## API endpointy

| Metoda | Endpoint | Popis |
|--------|----------|-------|
| GET | `/api/destinations` | Seznam sledovaných destinací |
| GET | `/api/summary` | Nejlevnější ceny pro všechny destinace |
| GET | `/api/prices/{iata}` | Historie cen pro destinaci |
| GET | `/api/prices/{iata}/stats` | Statistiky (min/max/průměr) |
| GET | `/api/prices/{iata}/chart` | Data pro čárový graf |
| GET | `/api/snapshots` | Log posledních sběrů |

Plná dokumentace API dostupná na `http://localhost:8000/docs` po spuštění backendu.

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
stops, duration_minutes, collected_at
```

### `snapshots` – metadata sběrů (monitoring)
```
id, collected_at, source, route, status, records_saved, error_message
```

---

## Struktura projektu

```
flightradar/
├── config.py            # Destinace, trasy, konstanty
├── database.py          # SQLAlchemy modely + init
├── normalizer.py        # Převod měn do EUR
├── main.py              # Hlavní spouštěč sběru
├── scrapers/
│   ├── ryanair.py       # Ryanair (ryanair-py)
│   ├── wizzair.py       # Wizzair (neoficiální API)
│   └── amadeus.py       # Qatar Airways + Emirates (Amadeus SDK)
├── api/
│   └── app.py           # FastAPI backend
├── frontend/
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── Header.jsx       # Hlavička aplikace
│           ├── Summary.jsx      # Karty destinací s indikátory
│           ├── RouteDetail.jsx  # Detail destinace
│           ├── PriceChart.jsx   # Čárový graf vývoje cen
│           ├── PriceTable.jsx   # Tabulka letů (řaditelná)
│           └── SnapshotLog.jsx  # Monitoring sběrů
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Cron job (automatický sběr)

Přidej do crontabu (`crontab -e`):

```cron
# Každý den ve 3:00 ráno
0 3 * * * /usr/bin/python3 /cesta/k/flightradar/main.py >> /var/log/flightradar.log 2>&1
```

---

## Konfigurace destinací

Destinace a trasy se konfigurují v `config.py`:

```python
DESTINATIONS = [
    {
        "name": "Japonsko – Tokio",
        "iata": "NRT",
        "flag": "🇯🇵",
        "airlines": ["amadeus"],  # které scrapery použít
    },
    # ...
]
```

---

## Poznámky

- **Ryanair a Wizzair** nemají veřejné API – použití je v šedé právní zóně (ToS)
- **Amadeus sandbox** vrací testovací data; pro reálné ceny přepni `AMADEUS_ENV=production` v `.env`
- Všechny ceny jsou normalizovány do **EUR** pro srovnatelnost
- Při blokování IP Ryanairu / Wizzairu zvaž rotaci IP nebo proxy

---

## Licence

Osobní projekt, není určen pro komerční využití.
