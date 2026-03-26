"""
FlightRadar – hlavní spouštěč.
Volá všechny scrapery, normalizuje data a ukládá do DB.

Použití:
  python main.py                  # sbírá všechny trasy
  python main.py --airline ryanair
  python main.py --dest LIS
  python main.py --dry-run        # jen zobrazí co by sbíralo, neuloží
"""

import argparse
import logging
import sys
from datetime import datetime

import config
import database as db
from scrapers import ryanair, wizzair, amadeus

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("flightradar.main")

SCRAPER_MAP = {
    "ryanair": ryanair,
    "wizzair": wizzair,
    "amadeus": amadeus,
}


def run(airline_filter: str | None = None,
        dest_filter: str | None = None,
        dry_run: bool = False):
    """Hlavní logika sběru dat."""

    db.init_db()

    routes = config.get_routes()

    if airline_filter:
        routes = [r for r in routes if r["airline"] == airline_filter.lower()]
    if dest_filter:
        routes = [r for r in routes if r["destination"] == dest_filter.upper()]

    if not routes:
        logger.warning("Žádné trasy k zpracování.")
        return

    total_saved = 0
    errors = 0

    with db.get_session() as session:
        for route_cfg in routes:
            origin = route_cfg["origin"]
            destination = route_cfg["destination"]
            airline = route_cfg["airline"]
            route_label = f"{origin}→{destination}"

            scraper = SCRAPER_MAP.get(airline)
            if scraper is None:
                logger.error(f"Neznámý scraper: {airline}")
                continue

            logger.info(f"▶  Sbírám {route_label} [{airline}]")

            try:
                prices = scraper.collect(origin, destination)
            except Exception as e:
                logger.error(f"Kritická chyba scraperu {airline} pro {route_label}: {e}")
                db.save_snapshot(session, airline, route_label, "error", error=str(e))
                errors += 1
                continue

            if not prices:
                logger.info(f"   → Žádné výsledky.")
                db.save_snapshot(session, airline, route_label, "empty")
                continue

            if dry_run:
                cheapest = min(prices, key=lambda p: p["price_eur"])
                logger.info(
                    f"   [DRY RUN] {len(prices)} letů, nejlevnější: "
                    f"{cheapest['price_eur']}€ dne {cheapest['departure_date']}"
                )
                continue

            # Najdi nebo vytvoř Route záznam v DB
            db_route = session.query(db.Route).filter_by(
                origin_iata=origin,
                destination_iata=destination,
                airline=airline,
            ).first()

            if db_route is None:
                logger.error(f"Trasa {route_label} [{airline}] nenalezena v DB – přeskakuji.")
                continue

            saved = db.save_prices(session, db_route, prices)
            db.save_snapshot(session, airline, route_label, "ok", records=saved)
            total_saved += saved

            cheapest = min(prices, key=lambda p: p["price_eur"])
            logger.info(
                f"   ✓ Uloženo {saved} záznamů | "
                f"Nejlevnější: {cheapest['price_eur']}€ "
                f"({cheapest.get('airline_detail', airline)}) "
                f"dne {cheapest['departure_date']}"
            )

    logger.info(f"═══ Hotovo. Uloženo {total_saved} záznamů. Chyb: {errors}. ═══")


def main():
    parser = argparse.ArgumentParser(
        description="FlightRadar – sběr cen letenek z Prahy"
    )
    parser.add_argument(
        "--airline", "-a",
        choices=list(SCRAPER_MAP.keys()),
        help="Sbírej jen pro jednu aerolinku",
    )
    parser.add_argument(
        "--dest", "-d",
        choices=[d["iata"] for d in config.DESTINATIONS],
        help="Sbírej jen pro jednu destinaci (IATA kód)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pouze zobraz výsledky, neukládej do DB",
    )
    args = parser.parse_args()
    run(
        airline_filter=args.airline,
        dest_filter=args.dest,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
