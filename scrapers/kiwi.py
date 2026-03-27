"""
FlightRadar – Kiwi.com Playwright scraper.
Zachytává GraphQL odpovědi z api.skypicker.com bez API klíče.
Spouští headless Chromium přes Playwright.
"""

import logging
import json
from datetime import date, timedelta

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import config
from normalizer import normalize_many

logger = logging.getLogger(__name__)

KIWI_CITY_SLUGS = {
    "PRG": "prague-czech-republic",
    "LIS": "lisbon-portugal",
    "FNC": "funchal-madeira-portugal",
    "NRT": "tokyo-japan",
    "OKA": "okinawa-japan",
}


def _build_url(origin: str, destination: str, dep_date: date, max_stops: int = 2) -> str:
    origin_slug = KIWI_CITY_SLUGS.get(origin, origin.lower())
    dest_slug = KIWI_CITY_SLUGS.get(destination, destination.lower())
    date_str = dep_date.strftime("%Y-%m-%d")
    return (
        f"https://www.kiwi.com/en/search/results/{origin_slug}/{dest_slug}"
        f"/{date_str}/no-return/?stopNumber={max_stops}"
    )


def _parse_itinerary(it: dict, dep_date: date, max_stops: int) -> dict | None:
    """
    Převede GraphQL itinerary na surový záznam.
    Kiwi OnePerCity itineráře obsahují jen cenu – datum bereme z URL.
    """
    try:
        price_eur = float(it.get("priceEur", {}).get("amount", 0))
        if price_eur <= 0:
            return None

        # Detailní segmenty (pokud jsou k dispozici)
        carriers = set()
        stops = max_stops  # fallback = filtr co jsme zadali
        duration = None

        for sector_key in ("sectors", "outbound", "inbound"):
            sectors = it.get(sector_key, [])
            if not isinstance(sectors, list):
                continue
            for sector in sectors:
                for seg in sector.get("sectorSegments", []):
                    segment = seg.get("segment", {})
                    carrier = segment.get("carrier", {})
                    name = carrier.get("name", "") or carrier.get("code", "")
                    if name:
                        carriers.add(name)
            if sectors:
                stops = max(0, sum(
                    max(0, len(s.get("sectorSegments", [])) - 1)
                    for s in sectors
                ))

        return {
            "price": price_eur,
            "currency": "EUR",
            "departure_date": str(dep_date),
            "airline_detail": ", ".join(sorted(carriers)) if carriers else "",
            "flight_numbers": "",
            "stops": stops,
            "duration_minutes": duration,
        }
    except Exception as e:
        logger.warning(f"Nelze parsovat Kiwi itinerary: {e}")
        return None


def _scrape_date(origin: str, destination: str, dep_date: date, max_stops: int) -> list[dict]:
    """Spustí Playwright, načte Kiwi stránku a zachytí GraphQL odpovědi."""
    url = _build_url(origin, destination, dep_date, max_stops)
    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def on_response(response):
                if "skypicker.com" in response.url and "graphql" in response.url:
                    try:
                        data = response.json()
                        gql_data = data.get("data", {})
                        # Projdi všechny klíče v GraphQL odpovědi
                        for key, val in gql_data.items():
                            if not isinstance(val, dict):
                                continue
                            itineraries = val.get("itineraries", [])
                            for it in itineraries:
                                parsed = _parse_itinerary(it, dep_date, max_stops)
                                if parsed:
                                    results.append(parsed)
                    except Exception:
                        pass

            page.on("response", on_response)
            page.goto(url, timeout=35000, wait_until="networkidle")
            page.wait_for_timeout(4000)  # počkej na GraphQL odpovědi
            browser.close()

    except PlaywrightTimeout:
        logger.warning(f"Kiwi timeout pro {origin}→{destination} {dep_date}")
    except Exception as e:
        logger.error(f"Kiwi chyba pro {origin}→{destination} {dep_date}: {e}")

    return results


def collect(origin: str, destination: str) -> list[dict]:
    """
    Sbírá Kiwi.com lety přes Playwright pro prodloužené víkendy.
    Prochází každý 2. prodloužený víkend aby šetřil čas.
    """
    dest_cfg = config.DESTINATION_MAP.get(destination, {})
    max_stops = dest_cfg.get("max_stops", 1)
    search_days = dest_cfg.get("search_days", config.SEARCH_DAYS_AHEAD)

    weekend_dates = config.get_extended_weekend_dates(search_days)
    # Každý 2. datum (šetří čas – lety na sousední dny bývají podobné ceny)
    sampled = weekend_dates[::2]

    logger.info(
        f"Kiwi: hledám {origin}→{destination}, "
        f"{len(sampled)} datumů, max_stops={max_stops}"
    )

    raw_all = []
    for dep_date in sampled:
        found = _scrape_date(origin, destination, dep_date, max_stops)
        if found:
            cheapest = min(found, key=lambda x: x["price"])
            raw_all.append(cheapest)
            logger.debug(
                f"  {dep_date}: {cheapest['price']}€ "
                f"({cheapest['airline_detail']}, {cheapest['stops']} přestupů)"
            )

    logger.info(f"Kiwi: celkem {len(raw_all)} výsledků pro {origin}→{destination}")
    return normalize_many(raw_all)
