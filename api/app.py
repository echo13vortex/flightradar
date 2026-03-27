"""
FlightRadar – FastAPI backend.

Endpointy:
  GET /api/destinations          – seznam sledovaných destinací
  GET /api/prices/{iata}         – historie cen pro destinaci
  GET /api/prices/{iata}/stats   – statistiky (min/max/průměr)
  GET /api/prices/{iata}/chart   – data pro čárový graf (daily cheapest)
  GET /api/summary               – přehled nejlevnějších cen pro všechny destinace
  GET /api/snapshots             – poslední sběry (monitoring)

Spuštění:
  uvicorn api.app:app --reload --port 8002
  PORT=8002 uvicorn api.app:app --reload
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, and_

import config
import database as db

app = FastAPI(
    title="FlightRadar API",
    description="Sledování cen letenek z Prahy (PRG)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # v produkci omez na doménu frontendu
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Pydantic schémata ─────────────────────────────────────────────────────────

class DestinationOut(BaseModel):
    iata: str
    name: str
    flag: str
    notes: str
    airlines: list[str]


class PriceOut(BaseModel):
    id: int
    price_eur: float
    departure_date: date
    airline_detail: Optional[str]
    stops: int
    duration_minutes: Optional[int]
    collected_at: datetime

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    iata: str
    name: str
    min_eur: Optional[float]
    max_eur: Optional[float]
    avg_eur: Optional[float]
    current_cheapest_eur: Optional[float]
    current_cheapest_date: Optional[date]
    current_cheapest_airline: Optional[str]
    is_below_avg: bool
    days_analyzed: int


class ChartPoint(BaseModel):
    collected_date: date
    min_price_eur: float
    airline: Optional[str]


class SummaryItem(BaseModel):
    iata: str
    name: str
    flag: str
    min_eur: Optional[float]
    avg_eur: Optional[float]
    current_cheapest_eur: Optional[float]
    current_cheapest_date: Optional[date]
    current_cheapest_airline: Optional[str]
    is_below_avg: bool


class SnapshotOut(BaseModel):
    id: int
    collected_at: datetime
    source: str
    route: Optional[str]
    status: str
    records_saved: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


# ── Endpointy ─────────────────────────────────────────────────────────────────

@app.get("/api/destinations", response_model=list[DestinationOut])
def get_destinations():
    """Vrátí seznam sledovaných destinací."""
    return [
        DestinationOut(
            iata=d["iata"],
            name=d["name"],
            flag=d["flag"],
            notes=d["notes"],
            airlines=d["airlines"],
        )
        for d in config.DESTINATIONS
    ]


@app.get("/api/prices/{iata}", response_model=list[PriceOut])
def get_prices(
    iata: str,
    days: int = Query(default=90, ge=1, le=365, description="Kolik dní zpět"),
    airline: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    """Historie nasbíraných cen pro destinaci."""
    iata = iata.upper()
    _check_destination(iata)

    since = datetime.utcnow() - timedelta(days=days)

    with db.get_session() as session:
        query = (
            session.query(db.Price)
            .join(db.Route)
            .filter(
                db.Route.destination_iata == iata,
                db.Price.collected_at >= since,
            )
        )
        if airline:
            query = query.filter(db.Route.airline == airline.lower())

        prices = (
            query
            .order_by(db.Price.departure_date, db.Price.price_eur)
            .limit(limit)
            .all()
        )
        return prices


@app.get("/api/prices/{iata}/stats", response_model=StatsOut)
def get_stats(
    iata: str,
    days: int = Query(default=30, ge=1, le=365),
):
    """Statistiky cen (min/max/avg) za posledních N dní sběru."""
    iata = iata.upper()
    dest = _check_destination(iata)

    since = datetime.utcnow() - timedelta(days=days)

    with db.get_session() as session:
        agg = (
            session.query(
                func.min(db.Price.price_eur).label("min_eur"),
                func.max(db.Price.price_eur).label("max_eur"),
                func.avg(db.Price.price_eur).label("avg_eur"),
                func.count(db.Price.id).label("cnt"),
            )
            .join(db.Route)
            .filter(
                db.Route.destination_iata == iata,
                db.Price.collected_at >= since,
            )
            .one()
        )

        # Aktuálně nejlevnější let na budoucí datum
        cheapest = (
            session.query(db.Price)
            .join(db.Route)
            .filter(
                db.Route.destination_iata == iata,
                db.Price.departure_date >= date.today(),
            )
            .order_by(db.Price.price_eur)
            .first()
        )

        avg = float(agg.avg_eur) if agg.avg_eur else None
        current = float(cheapest.price_eur) if cheapest else None

        return StatsOut(
            iata=iata,
            name=dest["name"],
            min_eur=float(agg.min_eur) if agg.min_eur else None,
            max_eur=float(agg.max_eur) if agg.max_eur else None,
            avg_eur=round(avg, 2) if avg else None,
            current_cheapest_eur=current,
            current_cheapest_date=cheapest.departure_date if cheapest else None,
            current_cheapest_airline=cheapest.airline_detail if cheapest else None,
            is_below_avg=bool(current and avg and current < avg),
            days_analyzed=int(agg.cnt or 0),
        )


@app.get("/api/prices/{iata}/chart", response_model=list[ChartPoint])
def get_chart_data(
    iata: str,
    days: int = Query(default=30, ge=7, le=180),
):
    """
    Denní minimum cen – pro čárový graf vývoje cen v čase.
    Každý bod = nejnižší cena nasbíraná v daný den.
    """
    iata = iata.upper()
    _check_destination(iata)

    since = datetime.utcnow() - timedelta(days=days)

    with db.get_session() as session:
        rows = (
            session.query(
                func.date(db.Price.collected_at).label("cdate"),
                func.min(db.Price.price_eur).label("min_price"),
            )
            .join(db.Route)
            .filter(
                db.Route.destination_iata == iata,
                db.Price.collected_at >= since,
            )
            .group_by(func.date(db.Price.collected_at))
            .order_by(func.date(db.Price.collected_at))
            .all()
        )

        # Přidáme název aerolinky pro nejlevnější cenu v daný den
        points = []
        for row in rows:
            cdate = row.cdate
            if isinstance(cdate, str):
                cdate = date.fromisoformat(cdate)
            cheapest_that_day = (
                session.query(db.Price)
                .join(db.Route)
                .filter(
                    db.Route.destination_iata == iata,
                    func.date(db.Price.collected_at) == row.cdate,
                    db.Price.price_eur == row.min_price,
                )
                .first()
            )
            points.append(ChartPoint(
                collected_date=cdate,
                min_price_eur=row.min_price,
                airline=cheapest_that_day.airline_detail if cheapest_that_day else None,
            ))
        return points


@app.get("/api/summary", response_model=list[SummaryItem])
def get_summary():
    """Přehled aktuálně nejlevnějších cen pro všechny destinace."""
    result = []
    with db.get_session() as session:
        for dest in config.DESTINATIONS:
            iata = dest["iata"]

            agg = (
                session.query(
                    func.min(db.Price.price_eur).label("min_eur"),
                    func.avg(db.Price.price_eur).label("avg_eur"),
                )
                .join(db.Route)
                .filter(db.Route.destination_iata == iata)
                .one()
            )

            cheapest = (
                session.query(db.Price)
                .join(db.Route)
                .filter(
                    db.Route.destination_iata == iata,
                    db.Price.departure_date >= date.today(),
                )
                .order_by(db.Price.price_eur)
                .first()
            )

            avg = float(agg.avg_eur) if agg.avg_eur else None
            current = float(cheapest.price_eur) if cheapest else None

            result.append(SummaryItem(
                iata=iata,
                name=dest["name"],
                flag=dest["flag"],
                min_eur=float(agg.min_eur) if agg.min_eur else None,
                avg_eur=round(avg, 2) if avg else None,
                current_cheapest_eur=current,
                current_cheapest_date=cheapest.departure_date if cheapest else None,
                current_cheapest_airline=cheapest.airline_detail if cheapest else None,
                is_below_avg=bool(current and avg and current < avg),
            ))

    return result


@app.get("/api/snapshots", response_model=list[SnapshotOut])
def get_snapshots(limit: int = Query(default=50, ge=1, le=200)):
    """Posledních N sběrů pro monitoring."""
    with db.get_session() as session:
        return (
            session.query(db.Snapshot)
            .order_by(db.Snapshot.collected_at.desc())
            .limit(limit)
            .all()
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_destination(iata: str) -> dict:
    dest = config.DESTINATION_MAP.get(iata)
    if not dest:
        raise HTTPException(status_code=404, detail=f"Destinace '{iata}' není sledována.")
    return dest


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port, reload=True)
