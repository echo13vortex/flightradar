"""
FlightRadar – Amadeus API scraper.
Používá amadeus-python SDK pro Qatar Airways a Emirates.

Pokryté trasy z PRG (s přestupy):
  PRG → NRT  (Tokio – Qatar přes DOH, Emirates přes DXB)
  PRG → OKA  (Okinawa – přes Tokio)
  PRG → FNC  (Madeira – různé aerolinky)
  PRG → LIS  (Lisabon – různé aerolinky)

API: https://developers.amadeus.com
Proměnné prostředí: AMADEUS_API_KEY, AMADEUS_API_SECRET
"""

import logging
from datetime import date, timedelta

import config
from normalizer import normalize_many

logger = logging.getLogger(__name__)

# Aerolinky, které chceme preferovat (filtrujeme výsledky)
PREFERRED_AIRLINES = {
    "QR": "Qatar Airways",
    "EK": "Emirates",
    "TP": "TAP Air Portugal",
    "FR": "Ryanair",
    "W6": "Wizzair",
    "LH": "Lufthansa",
    "OS": "Austrian Airlines",
    "OK": "Czech Airlines",
}


def _get_client():
    """Vytvoří Amadeus klienta. Vrátí None pokud chybí credentials."""
    try:
        from amadeus import Client, ResponseError
    except ImportError:
        logger.error("Knihovna 'amadeus' není nainstalována. Spusť: pip install amadeus")
        return None, None

    if not config.AMADEUS_API_KEY or not config.AMADEUS_API_SECRET:
        logger.error(
            "Amadeus API klíče nejsou nastaveny. "
            "Nastav AMADEUS_API_KEY a AMADEUS_API_SECRET v .env souboru."
        )
        return None, None

    client = Client(
        client_id=config.AMADEUS_API_KEY,
        client_secret=config.AMADEUS_API_SECRET,
        hostname="test" if config.AMADEUS_ENV == "test" else "production",
        log_level="silent",
    )
    return client, ResponseError


def _duration_to_minutes(iso_duration: str) -> int | None:
    """Převede ISO 8601 duration (PT14H30M) na minuty."""
    if not iso_duration:
        return None
    import re
    h = re.search(r'(\d+)H', iso_duration)
    m = re.search(r'(\d+)M', iso_duration)
    hours = int(h.group(1)) if h else 0
    mins = int(m.group(1)) if m else 0
    return hours * 60 + mins


def _parse_offer(offer: dict) -> dict | None:
    """Převede Amadeus flight offer na surový záznam."""
    try:
        price_info = offer.get("price", {})
        total = float(price_info.get("total", 0))
        currency = price_info.get("currency", "EUR")

        itineraries = offer.get("itineraries", [])
        if not itineraries:
            return None

        first_itin = itineraries[0]
        segments = first_itin.get("segments", [])
        if not segments:
            return None

        departure_date = segments[0]["departure"]["at"][:10]
        stops = len(segments) - 1
        duration = _duration_to_minutes(first_itin.get("duration", ""))

        # Kódy aerolinky (z prvního segmentu)
        carriers = list({s.get("carrierCode", "") for s in segments})
        airline_names = [PREFERRED_AIRLINES.get(c, c) for c in carriers]
        airline_detail = " + ".join(airline_names)

        flight_numbers = ",".join(
            f"{s.get('carrierCode','')}{s.get('number','')}" for s in segments
        )

        return {
            "price": total,
            "currency": currency,
            "departure_date": departure_date,
            "airline_detail": airline_detail,
            "flight_numbers": flight_numbers,
            "stops": stops,
            "duration_minutes": duration,
        }
    except Exception as e:
        logger.warning(f"Nelze parsovat Amadeus offer: {e}")
        return None


def _search_one_date(client, origin: str, destination: str, dep_date: date) -> list[dict]:
    """Volá Amadeus flight-offers pro jeden datum odletu."""
    from amadeus import ResponseError
    try:
        response = client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=dep_date.strftime("%Y-%m-%d"),
            adults=config.ADULT_COUNT,
            max=10,
            currencyCode=config.BASE_CURRENCY,
        )
        return response.data or []
    except ResponseError as e:
        # 400 = no flights found – normální stav
        if hasattr(e, 'response') and e.response and e.response.status_code == 400:
            return []
        logger.warning(f"Amadeus ResponseError pro {origin}→{destination} {dep_date}: {e}")
        return []
    except Exception as e:
        logger.error(f"Amadeus chyba: {e}")
        return []


def collect(origin: str, destination: str) -> list[dict]:
    """
    Sbírá Amadeus lety z `origin` do `destination` pro příštích N dní.
    Prochází každý 7. den (weekly sampling) aby šetřilo API volání.
    Vrátí normalizované záznamy.
    """
    client, _ = _get_client()
    if client is None:
        return []

    date_from, date_to = config.get_date_range()
    logger.info(f"Amadeus: hledám {origin}→{destination} od {date_from} do {date_to}")

    raw_all = []
    current = date_from

    while current <= date_to:
        offers = _search_one_date(client, origin, destination, current)
        raw = [_parse_offer(o) for o in offers]
        raw_all.extend([r for r in raw if r is not None])
        current += timedelta(days=7)  # weekly sampling

    logger.info(f"Amadeus: nalezeno {len(raw_all)} nabídek {origin}→{destination}")
    return normalize_many(raw_all)
