"""
FlightRadar – Travelpayouts / Aviasales Data API scraper.

Endpoint: /v2/prices/latest  (cached data, zdarma, 200 req/hod)
Pokrývá všechny aerolinky na trase PRG → LIS / FNC / NRT / OKA.

Registrace + API token: https://www.travelpayouts.com
Token nastav jako TRAVELPAYOUTS_TOKEN v .env souboru.
"""

import logging
from datetime import date

import requests

import config
from normalizer import normalize_many

logger = logging.getLogger(__name__)

BASE_URL = "https://api.travelpayouts.com"
SESSION = requests.Session()


def _get_token() -> str | None:
    token = config.TRAVELPAYOUTS_TOKEN
    if not token:
        logger.error(
            "TRAVELPAYOUTS_TOKEN není nastaven. "
            "Registruj se na travelpayouts.com a nastav token v .env souboru."
        )
        return None
    return token


def _fetch_latest(origin: str, destination: str, token: str) -> list[dict]:
    """Stáhne nejnovější cached ceny pro trasu (period_type=year)."""
    url = f"{BASE_URL}/v2/prices/latest"
    params = {
        "origin": origin,
        "destination": destination,
        "currency": config.BASE_CURRENCY,
        "period_type": "year",
        "limit": 1000,
        "show_to_affiliates": "true",
        "token": token,
    }
    try:
        r = SESSION.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            logger.warning(f"Travelpayouts API vrátilo success=false pro {origin}→{destination}")
            return []
        return data.get("data", [])
    except requests.HTTPError as e:
        logger.error(f"Travelpayouts HTTP chyba {e.response.status_code}: {e}")
        return []
    except Exception as e:
        logger.error(f"Travelpayouts chyba: {e}")
        return []


def _fetch_monthly(origin: str, destination: str, token: str) -> list[dict]:
    """
    Stáhne nejlevnější ceny po měsících (/v1/prices/cheap).
    Volá pro každý měsíc na rok dopředu.
    """
    from datetime import datetime, timedelta
    results = []
    today = date.today()

    for month_offset in range(12):
        year = today.year + (today.month + month_offset - 1) // 12
        month = (today.month + month_offset - 1) % 12 + 1
        depart_date = f"{year}-{month:02d}"

        url = f"{BASE_URL}/v1/prices/cheap"
        params = {
            "origin": origin,
            "destination": destination,
            "depart_date": depart_date,
            "currency": config.BASE_CURRENCY,
            "token": token,
        }
        try:
            r = SESSION.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get("success") and data.get("data"):
                # data["data"] = { "LIS": { "0": {flight}, "1": {flight}, ... } }
                # klíče jsou počty zastávek (0=přímý, 1=1 přestup, ...)
                for dest_code, stops_dict in data["data"].items():
                    if not isinstance(stops_dict, dict):
                        continue
                    for stops_count, info in stops_dict.items():
                        if not isinstance(info, dict):
                            continue
                        price = float(info.get("price", 0))
                        if price <= 0:
                            continue
                        dep = info.get("departure_at", f"{depart_date}-01")[:10]
                        results.append({
                            "price": price,
                            "currency": config.BASE_CURRENCY,
                            "departure_date": dep,
                            "airline_detail": info.get("airline", ""),
                            "flight_numbers": str(info.get("flight_number", "")),
                            "stops": int(stops_count) if stops_count.isdigit() else 0,
                            "duration_minutes": info.get("duration_to"),
                        })
        except Exception as e:
            logger.warning(f"Travelpayouts /cheap chyba pro {depart_date}: {e}")

    return results


def _parse_latest_item(item: dict) -> dict | None:
    """Převede jeden záznam z /v2/prices/latest na surový slovník."""
    try:
        price = float(item.get("value", 0))
        if price <= 0:
            return None

        dep_date = item.get("depart_date", "")
        if not dep_date:
            return None

        return {
            "price": price,
            "currency": config.BASE_CURRENCY,
            "departure_date": dep_date[:10],
            "airline_detail": item.get("airline", ""),
            "flight_numbers": item.get("flight_number_outbound_name", ""),
            "stops": item.get("number_of_changes", 0),
            "duration_minutes": None,
        }
    except Exception as e:
        logger.warning(f"Nelze parsovat Travelpayouts záznam: {e}")
        return None


def collect(origin: str, destination: str) -> list[dict]:
    """
    Sbírá ceny z Travelpayouts pro trasu origin→destination.
    Kombinuje /v2/prices/latest (broad) + /v1/prices/cheap (po měsících).
    Vrátí normalizované záznamy filtrované na prodloužené víkendy (Čt+Pá).
    """
    token = _get_token()
    if not token:
        return []

    logger.info(f"Travelpayouts: hledám {origin}→{destination}")

    # Primární zdroj – latest prices
    raw_all = []
    latest = _fetch_latest(origin, destination, token)
    parsed = [_parse_latest_item(item) for item in latest]
    raw_all.extend([p for p in parsed if p is not None])

    # Doplňkový zdroj – cheapest by month (zachytí i to co latest nezahrnuje)
    monthly = _fetch_monthly(origin, destination, token)
    raw_all.extend(monthly)

    # Odstraň duplicity dle (departure_date, price)
    seen = set()
    unique = []
    for r in raw_all:
        key = (r["departure_date"], r["price"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Filtruj jen prodloužené víkendy (čtvrtek=3, pátek=4)
    weekend_dates = {str(d) for d in config.get_extended_weekend_dates()}
    unique = [r for r in unique if str(r["departure_date"]) in weekend_dates]

    logger.info(
        f"Travelpayouts: nalezeno {len(unique)} letů na prodloužené víkendy "
        f"{origin}→{destination}"
    )
    return normalize_many(unique)
