"""
FlightRadar – databázové modely a připojení (SQLAlchemy + SQLite/PostgreSQL).
"""

import logging
from datetime import datetime, date

from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Date, Boolean, Text, ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.exc import IntegrityError

import config

logger = logging.getLogger(__name__)

# ── Engine + Session ──────────────────────────────────────────────────────────
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ── Modely ────────────────────────────────────────────────────────────────────

class Route(Base):
    """Sledovaná trasa, např. PRG → NRT přes Qatar Airways."""
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True)
    origin_iata = Column(String(3), nullable=False)
    destination_iata = Column(String(3), nullable=False)
    destination_name = Column(String(100), nullable=False)
    airline = Column(String(50), nullable=False)   # "ryanair" | "wizzair" | "amadeus"
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prices = relationship("Price", back_populates="route", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("origin_iata", "destination_iata", "airline", name="uq_route"),
    )

    def __repr__(self):
        return f"<Route {self.origin_iata}→{self.destination_iata} [{self.airline}]>"


class Price(Base):
    """Jeden denní sběr ceny pro trasu na konkrétní datum odletu."""
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    price_eur = Column(Float, nullable=False)        # normalizovaná cena v EUR
    price_original = Column(Float, nullable=True)    # původní cena
    currency_original = Column(String(3), nullable=True)
    departure_date = Column(Date, nullable=False)    # datum odletu
    return_date = Column(Date, nullable=True)        # datum návratu (None = one-way)
    airline_detail = Column(String(100), nullable=True)  # konkrétní aerolinka (Qatar, Emirates...)
    flight_numbers = Column(String(200), nullable=True)   # např. "QR284,QR820"
    stops = Column(Integer, default=0)               # počet přestupů
    duration_minutes = Column(Integer, nullable=True)
    departure_time = Column(String(5), nullable=True)    # "HH:MM"
    arrival_time = Column(String(5), nullable=True)      # "HH:MM"
    source_url = Column(String(500), nullable=True)      # odkaz na kiwi.com pro ověření
    collected_at = Column(DateTime, default=datetime.utcnow)

    route = relationship("Route", back_populates="prices")

    __table_args__ = (
        Index("ix_prices_route_departure", "route_id", "departure_date"),
        Index("ix_prices_collected", "collected_at"),
    )

    def __repr__(self):
        return f"<Price {self.price_eur:.0f}€ dep={self.departure_date}>"


class Snapshot(Base):
    """Metadata každého sběru – pro debugging a monitoring."""
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), nullable=False)   # "ryanair" | "wizzair" | "amadeus"
    route = Column(String(20), nullable=True)     # "PRG→LIS"
    status = Column(String(20), nullable=False)   # "ok" | "error" | "empty"
    records_saved = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Snapshot {self.source} {self.status} @ {self.collected_at}>"


# ── Pomocné funkce ────────────────────────────────────────────────────────────

def init_db():
    """Vytvoří tabulky a naplní trasy z configu."""
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    _seed_routes()
    logger.info("Databáze inicializována.")


def _migrate_db():
    """Přidá chybějící sloupce do existujících tabulek (SQLite nemá ALTER TABLE IF NOT EXISTS)."""
    migrations = [
        ("prices", "departure_time", "VARCHAR(5)"),
        ("prices", "arrival_time", "VARCHAR(5)"),
        ("prices", "source_url", "VARCHAR(500)"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                    )
                )
                conn.commit()
                logger.info(f"Migrace: přidán sloupec {table}.{column}")
            except Exception:
                pass  # sloupec již existuje


def _seed_routes():
    """Vloží trasy z config.py (pokud ještě neexistují)."""
    with SessionLocal() as session:
        for route_cfg in config.get_routes():
            exists = session.query(Route).filter_by(
                origin_iata=route_cfg["origin"],
                destination_iata=route_cfg["destination"],
                airline=route_cfg["airline"],
            ).first()
            if not exists:
                session.add(Route(
                    origin_iata=route_cfg["origin"],
                    destination_iata=route_cfg["destination"],
                    destination_name=route_cfg["destination_name"],
                    airline=route_cfg["airline"],
                ))
        session.commit()


def get_session() -> Session:
    """Vrátí novou session (použij jako context manager)."""
    return SessionLocal()


def save_prices(session: Session, route: Route, prices: list[dict]) -> int:
    """
    Uloží seznam cen pro trasu. Každý záznam v `prices` musí mít klíče:
    price_eur, departure_date + volitelné: price_original, currency_original,
    airline_detail, flight_numbers, stops, duration_minutes, return_date
    """
    # Build set of existing (departure_date, price_eur, airline_detail) to skip duplicates
    existing = set(
        (str(r[0]), float(r[1]), r[2])
        for r in session.query(
            Price.departure_date, Price.price_eur, Price.airline_detail
        ).filter(Price.route_id == route.id).all()
    )

    saved = 0
    for p in prices:
        key = (str(p["departure_date"]), float(p["price_eur"]), p.get("airline_detail"))
        if key in existing:
            continue
        existing.add(key)
        price = Price(
            route_id=route.id,
            price_eur=p["price_eur"],
            price_original=p.get("price_original"),
            currency_original=p.get("currency_original"),
            departure_date=p["departure_date"],
            return_date=p.get("return_date"),
            airline_detail=p.get("airline_detail"),
            flight_numbers=p.get("flight_numbers"),
            stops=p.get("stops", 0),
            duration_minutes=p.get("duration_minutes"),
            departure_time=p.get("departure_time"),
            arrival_time=p.get("arrival_time"),
            source_url=p.get("source_url"),
        )
        session.add(price)
        saved += 1
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        logger.warning("Integrity error při ukládání cen – rollback.")
        saved = 0
    return saved


def save_snapshot(session: Session, source: str, route: str,
                  status: str, records: int = 0, error: str = None):
    session.add(Snapshot(
        source=source,
        route=route,
        status=status,
        records_saved=records,
        error_message=error,
    ))
    session.commit()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Inicializuj databázi")
    args = parser.parse_args()
    if args.init:
        logging.basicConfig(level=logging.INFO)
        init_db()
        print("Databáze připravena.")
