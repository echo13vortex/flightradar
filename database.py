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
    _seed_routes()
    logger.info("Databáze inicializována.")


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
    saved = 0
    for p in prices:
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
