"""
FlightRadar – Ryanair scraper.
Používá neoficiální knihovnu `ryanair-py`.

Pokryté trasy z PRG:
  PRG → LIS (Lisabon)
  PRG → FNC (Madeira/Funchal) – obvykle přes Porto nebo Sevilu

Poznámka: Ryanair nelétá do Japonska ani Okinawy.
"""

import logging
from datetime import date, timedelta

import config
from normalizer import normalize_many

logger = logging.getLogger(__name__)


def _parse_ryanair_flight(flight) -> dict | None:
    """Převede objekt z ryanair-py na surový slovník."""
    try:
        return {
            "price": flight.price,
            "currency": "EUR",  # ryanair-py vrací vždy v zadané měně
            "departure_date": flight.departureTime.date() if hasattr(flight.departureTime, "date") else flight.departureTime,
            "airline_detail": "Ryanair",
            "flight_numbers": getattr(flight, "flightNumber", None),
            "stops": 0,  # ryanair-py vrací přímé lety
        }
    except Exception as e:
        logger.warning(f"Nelze parsovat Ryanair flight: {e}")
        return None


def collect(origin: str, destination: str) -> list[dict]:
    """
    Sbírá nejlevnější Ryanair lety z `origin` do `destination`
    pro příštích N dní. Vrátí normalizované záznamy.
    """
    try:
        from ryanair import Ryanair
    except ImportError:
        logger.error("Knihovna 'ryanair-py' není nainstalována. Spusť: pip install ryanair-py")
        return []

    date_from, date_to = config.get_date_range()

    logger.info(f"Ryanair: hledám {origin}→{destination} od {date_from} do {date_to}")

    try:
        api = Ryanair("EUR")
        flights = api.get_cheapest_flights(
            airport=origin,
            date_from=date_from,
            date_to=date_to,
            destination_country=None,
            custom_params={"ToUniqueId": destination},
        )
    except TypeError:
        # Starší verze ryanair-py bez custom_params
        try:
            api = Ryanair("EUR")
            flights = api.get_cheapest_flights(origin, date_from, date_to)
            # Filtrujeme jen na cílový letiště
            flights = [f for f in flights if getattr(f, "destination", "") == destination]
        except Exception as e:
            logger.error(f"Ryanair API chyba: {e}")
            return []
    except Exception as e:
        logger.error(f"Ryanair API chyba: {e}")
        return []

    raw = [_parse_ryanair_flight(f) for f in (flights or [])]
    raw = [r for r in raw if r is not None]

    # Filtruj jen prodloužené víkendy (čtvrtek=3, pátek=4)
    weekend_dates = {str(d) for d in config.get_extended_weekend_dates()}
    raw = [r for r in raw if str(r["departure_date"]) in weekend_dates]

    logger.info(f"Ryanair: nalezeno {len(raw)} letů na prodloužené víkendy {origin}→{destination}")
    return normalize_many(raw)
