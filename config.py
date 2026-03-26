"""
FlightRadar - konfigurace tras a nastavení.
Sleduje ceny letenek z Prahy (PRG) do vybraných destinací.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Základní nastavení ────────────────────────────────────────────────────────
ORIGIN = "PRG"  # Praha Václav Havel

# Počet dní dopředu pro hledání letů
SEARCH_DAYS_AHEAD = 180  # 6 měsíců

# Počet dospělých cestujících
ADULT_COUNT = 1

# Základní měna pro normalizaci
BASE_CURRENCY = "EUR"

# ── Destinace ─────────────────────────────────────────────────────────────────
DESTINATIONS = [
    {
        "name": "Japonsko – Tokio",
        "iata": "NRT",
        "country": "JP",
        "flag": "🇯🇵",
        "airlines": ["amadeus"],  # Qatar Airways / Emirates via Amadeus
        "notes": "Přestup nutný (obvykle Doha nebo Dubaj)",
    },
    {
        "name": "Okinawa – Naha",
        "iata": "OKA",
        "country": "JP",
        "flag": "🇯🇵",
        "airlines": ["amadeus"],  # Qatar / Emirates + Japan domestic
        "notes": "Přestup nutný (obvykle Tokio + domácí let v Japonsku)",
    },
    {
        "name": "Madeira – Funchal",
        "iata": "FNC",
        "country": "PT",
        "flag": "🇵🇹",
        "airlines": ["ryanair", "wizzair", "amadeus"],
        "notes": "Přímé lety nebo přes Lisabon / Porto",
    },
    {
        "name": "Lisabon",
        "iata": "LIS",
        "country": "PT",
        "flag": "🇵🇹",
        "airlines": ["ryanair", "wizzair", "amadeus"],
        "notes": "Přímé lety nebo přestup",
    },
]

# Rychlý lookup: IATA → destination dict
DESTINATION_MAP = {d["iata"]: d for d in DESTINATIONS}

# ── Trasy (origin → destination pro každou aerolinku) ─────────────────────────
def get_routes():
    """Vrátí seznam všech tras k sesbírání."""
    routes = []
    for dest in DESTINATIONS:
        for airline in dest["airlines"]:
            routes.append({
                "origin": ORIGIN,
                "destination": dest["iata"],
                "airline": airline,
                "destination_name": dest["name"],
            })
    return routes

# ── API klíče ─────────────────────────────────────────────────────────────────
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")  # "test" nebo "production"

# ── Databáze ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///flightradar.db")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Pomocné funkce ────────────────────────────────────────────────────────────
def get_search_dates():
    """Vrátí seznam datumů od zítřka po SEARCH_DAYS_AHEAD dní."""
    today = datetime.now().date()
    return [today + timedelta(days=i) for i in range(1, SEARCH_DAYS_AHEAD + 1)]

def get_date_range():
    """Vrátí (date_from, date_to) pro vyhledávání."""
    dates = get_search_dates()
    return dates[0], dates[-1]
