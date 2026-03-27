"""
FlightRadar – Kiwi.com Playwright scraper (jednosměrné lety).
Zachytává SearchOneWayItinerariesQuery z api.skypicker.com bez API klíče.

Hledá zvlášť:
  - odletový směr: PRG → LIS na čtvrtky a pátky
  - zpáteční směr: LIS → PRG na neděle a pondělky
"""

import logging
import random
import time
from datetime import date, timedelta

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import config
from normalizer import normalize_many

logger = logging.getLogger(__name__)

# Slugy měst pro Kiwi URL (formát který spustí SearchOneWayItinerariesQuery)
KIWI_CITY_SLUGS = {
    "PRG": "prague-czechia",
    "LIS": "lisbon-portugal",
    "FNC": "funchal-portugal",
    "NRT": "tokyo-japan",
    "OKA": "okinawa-japan",
}


def _build_url(origin: str, destination: str, dep_date: date) -> str:
    o = KIWI_CITY_SLUGS.get(origin, origin.lower())
    d = KIWI_CITY_SLUGS.get(destination, destination.lower())
    return (
        f"https://www.kiwi.com/en/search/results/{o}/{d}"
        f"/{dep_date.strftime('%Y-%m-%d')}/no-return/"
    )


def _parse_itinerary(it: dict, dep_date: date, max_stops: int | None) -> dict | None:
    try:
        price_eur = float(it.get("priceEur", {}).get("amount", 0))
        if price_eur <= 0:
            return None

        sector = it.get("sector", {}) or {}
        segs = sector.get("sectorSegments", [])
        if not segs:
            return None

        dep_time_raw = segs[0].get("segment", {}).get("source", {}).get("localTime", "")
        if not dep_time_raw:
            return None

        # Filter: only accept flights for the searched date
        if dep_time_raw[:10] != str(dep_date):
            return None

        arr_time_raw = segs[-1].get("segment", {}).get("destination", {}).get("localTime", "")

        stops = max(0, len(segs) - 1)
        if max_stops is not None and stops > max_stops:
            return None

        carriers = set()
        for seg in segs:
            name = seg.get("segment", {}).get("carrier", {}).get("name", "")
            if name:
                carriers.add(name)

        duration_raw = sector.get("duration", 0)
        duration_min = duration_raw // 60 if duration_raw else None

        return {
            "price": price_eur,
            "currency": "EUR",
            "departure_date": dep_time_raw[:10],
            "departure_time": dep_time_raw[11:16] if len(dep_time_raw) > 10 else None,
            "arrival_time": arr_time_raw[11:16] if len(arr_time_raw) > 10 else None,
            "airline_detail": ", ".join(sorted(carriers)),
            "flight_numbers": "",
            "stops": stops,
            "duration_minutes": duration_min,
        }
    except Exception as e:
        logger.warning(f"Nelze parsovat Kiwi itinerary: {e}")
        return None


def _scrape_oneway(origin: str, destination: str, dep_date: date, max_stops: int | None) -> list[dict]:
    """Načte Kiwi.com a vrátí jednosměrné lety pro daný den."""
    url = _build_url(origin, destination, dep_date)
    results = []
    gql_received = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            def on_response(response):
                nonlocal gql_received
                if "skypicker.com" in response.url and "SearchOneWay" in response.url:
                    gql_received = True
                    try:
                        data = response.json()
                        gql = data.get("data", {})
                        for val in gql.values():
                            if not isinstance(val, dict):
                                continue
                            for it in val.get("itineraries", []):
                                parsed = _parse_itinerary(it, dep_date, max_stops)
                                if parsed:
                                    results.append(parsed)
                    except Exception:
                        pass

            page.on("response", on_response)
            # Use "load" instead of "networkidle" — Kiwi keeps polling so networkidle
            # never fires within the timeout, causing excessive timeouts.
            page.goto(url, timeout=45000, wait_until="load")
            # Wait for GraphQL to arrive (up to 12s after page load)
            deadline = time.time() + 12
            while not gql_received and time.time() < deadline:
                page.wait_for_timeout(500)
            browser.close()

    except PlaywrightTimeout:
        logger.warning(f"Kiwi timeout: {origin}→{destination} {dep_date}")
    except Exception as e:
        logger.error(f"Kiwi chyba: {origin}→{destination} {dep_date}: {e}")

    return results


def collect(origin: str, destination: str) -> list[dict]:
    """
    Sbírá jednosměrné lety origin→destination na prodloužené víkendy.

    Odletový směr (PRG→LIS): čtvrtky + pátky
    Zpáteční směr (LIS→PRG): neděle + pondělky  ← přidáno automaticky v main workflow
    """
    dest_cfg = config.DESTINATION_MAP.get(destination, {})
    max_stops = dest_cfg.get("max_stops", None)
    search_days = dest_cfg.get("search_days", config.SEARCH_DAYS_AHEAD)

    # Odlet: čtvrtky (3) a pátky (4)
    weekend_dates = config.get_extended_weekend_dates(search_days)
    # Každý 2. datum aby to nebylo příliš pomalé
    sampled = weekend_dates[::2]

    logger.info(
        f"Kiwi: hledám {origin}→{destination} | "
        f"{len(sampled)} dat | max_stops={max_stops}"
    )

    raw_all = []
    for i, dep_date in enumerate(sampled):
        if i > 0:
            # Random delay 3–7s between requests to avoid throttling
            time.sleep(random.uniform(3, 7))
        found = _scrape_oneway(origin, destination, dep_date, max_stops)
        # Ulož jen nejlevnější let pro daný den
        if found:
            cheapest = min(found, key=lambda x: x["price"])
            raw_all.append(cheapest)
            logger.debug(
                f"  {dep_date}: {cheapest['price']:.0f}€ "
                f"({cheapest['airline_detail']}, {cheapest['stops']} st.)"
            )

    logger.info(f"Kiwi: {len(raw_all)} výsledků pro {origin}→{destination}")
    return normalize_many(raw_all)


def collect_return_leg(origin: str, destination: str, search_days: int | None = None, max_stops: int | None = None) -> list[dict]:
    """
    Sbírá jednosměrné lety origin→destination na zpáteční dny (Ne + Po).
    Používá se pro opačný směr (LIS→PRG).
    """
    if search_days is None:
        search_days = config.SEARCH_DAYS_AHEAD
    if max_stops is None:
        max_stops = None

    today = date.today()
    horizon = search_days or config.SEARCH_DAYS_AHEAD
    # Neděle (6) a pondělky (0)
    return_dates = [
        today + timedelta(days=i)
        for i in range(1, horizon + 1)
        if (today + timedelta(days=i)).weekday() in (6, 0)
    ]
    sampled = return_dates[::2]

    logger.info(
        f"Kiwi (zpáteční noga): hledám {origin}→{destination} | {len(sampled)} dat"
    )

    raw_all = []
    for i, dep_date in enumerate(sampled):
        if i > 0:
            time.sleep(random.uniform(3, 7))
        found = _scrape_oneway(origin, destination, dep_date, max_stops)
        if found:
            cheapest = min(found, key=lambda x: x["price"])
            raw_all.append(cheapest)

    logger.info(f"Kiwi (zpáteční): {len(raw_all)} výsledků pro {origin}→{destination}")
    return normalize_many(raw_all)
