"""
FlightRadar – Wizzair scraper.
Volá neoficiální Wizzair API (community reverse-engineering).

Pokryté trasy z PRG:
  PRG → LIS (Lisabon)
  PRG → FNC (Madeira/Funchal)

Poznámka: Wizzair nelétá do Japonska ani Okinawy.
⚠️  Neoficiální API – může přestat fungovat bez varování.
"""

import logging
import time
from datetime import date, timedelta

import requests

import config
from normalizer import normalize_many

logger = logging.getLogger(__name__)

# Wizzair mění verzi API – detekujeme ji z hlavní stránky nebo použijeme fixní
WIZZAIR_BASE = "https://be.wizzair.com"
WIZZAIR_API_VERSION = "21.4.0"   # aktualizuj dle potřeby

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://wizzair.com/",
    "Origin": "https://wizzair.com",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "x-requestedwith": "XMLHttpRequest",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _get_api_version() -> str:
    """Pokusí se detekovat aktuální verzi Wizzair API z JS bundle."""
    try:
        r = SESSION.get("https://wizzair.com/", timeout=10)
        import re
        match = re.search(r'be\.wizzair\.com/(\d+\.\d+\.\d+)', r.text)
        if match:
            version = match.group(1)
            logger.debug(f"Wizzair API verze detekována: {version}")
            return version
    except Exception as e:
        logger.debug(f"Nepodařilo se detekovat verzi Wizzair API: {e}")
    return WIZZAIR_API_VERSION


def _search_timetable(origin: str, destination: str, year: int, month: int) -> list[dict]:
    """
    Volá Wizzair timetable endpoint – vrátí dostupné lety v daném měsíci.
    """
    url = f"{WIZZAIR_BASE}/{WIZZAIR_API_VERSION}/Api/search/timetable"
    payload = {
        "flightList": [
            {
                "departureStation": origin,
                "arrivalStation": destination,
                "from": f"{year}-{month:02d}-01",
                "to": f"{year}-{month:02d}-28",
            }
        ],
        "priceType": "regular",
        "adultCount": config.ADULT_COUNT,
        "childCount": 0,
        "infantCount": 0,
    }
    try:
        r = SESSION.post(url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("outboundFlights", [])
    except requests.HTTPError as e:
        logger.warning(f"Wizzair timetable HTTP error {e.response.status_code}: {e}")
        return []
    except Exception as e:
        logger.error(f"Wizzair timetable chyba: {e}")
        return []


def _parse_flight(flight: dict) -> dict | None:
    """Převede raw Wizzair flight dict na surový záznam."""
    try:
        fares = flight.get("fares", [])
        if not fares:
            return None
        price = fares[0].get("price", {})
        amount = price.get("amount")
        currency = price.get("currencyCode", "EUR")
        if amount is None:
            return None

        dep_time = flight.get("departureDates", [None])[0]
        if not dep_time:
            return None

        return {
            "price": float(amount),
            "currency": currency,
            "departure_date": dep_time[:10],
            "airline_detail": "Wizzair",
            "flight_numbers": flight.get("flightNumber"),
            "stops": 0,
        }
    except Exception as e:
        logger.warning(f"Nelze parsovat Wizzair flight: {e}")
        return None


def collect(origin: str, destination: str) -> list[dict]:
    """
    Sbírá Wizzair lety z `origin` do `destination` pro příštích N měsíců.
    Vrátí normalizované záznamy.
    """
    from datetime import datetime

    logger.info(f"Wizzair: hledám {origin}→{destination}")

    raw_all = []
    today = date.today()

    # Projdi příštích 12 měsíců
    for month_offset in range(12):
        target = today.replace(day=1)
        # posun o month_offset měsíců
        year = today.year + (today.month + month_offset - 1) // 12
        month = (today.month + month_offset - 1) % 12 + 1

        flights = _search_timetable(origin, destination, year, month)
        raw = [_parse_flight(f) for f in flights]
        raw_all.extend([r for r in raw if r is not None])
        time.sleep(0.5)  # slušné chování vůči serveru

    # Filtruj jen prodloužené víkendy (čtvrtek=3, pátek=4)
    weekend_dates = {str(d) for d in config.get_extended_weekend_dates()}
    raw_all = [r for r in raw_all if str(r["departure_date"]) in weekend_dates]

    logger.info(f"Wizzair: nalezeno {len(raw_all)} letů na prodloužené víkendy {origin}→{destination}")
    return normalize_many(raw_all)
