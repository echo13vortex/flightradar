"""
FlightRadar – normalizace cen do EUR.
Statické kurzy jako fallback; při dostupnosti lze napojit live API.
"""

import logging

logger = logging.getLogger(__name__)

# Statické fallback kurzy (aktualizuj dle potřeby nebo napoj live API)
# Klíč = kód měny, hodnota = kurz vůči EUR (1 jednotka dané měny = X EUR)
EXCHANGE_RATES: dict[str, float] = {
    "EUR": 1.0,
    "CZK": 0.04,    # ~25 CZK = 1 EUR
    "GBP": 1.17,
    "USD": 0.92,
    "PLN": 0.23,
    "HUF": 0.0026,
    "RON": 0.20,
    "BGN": 0.51,
    "HRK": 0.133,
    "RSD": 0.0085,
    "CHF": 1.04,
    "NOK": 0.086,
    "SEK": 0.088,
    "DKK": 0.134,
    "JPY": 0.0063,
    "AED": 0.25,
    "QAR": 0.253,
}


def to_eur(amount: float, currency: str) -> float:
    """Převede částku z dané měny na EUR."""
    currency = currency.upper().strip()
    if currency == "EUR":
        return round(amount, 2)
    rate = EXCHANGE_RATES.get(currency)
    if rate is None:
        logger.warning(f"Neznámá měna '{currency}', ponechávám původní hodnotu jako EUR.")
        return round(amount, 2)
    return round(amount * rate, 2)


def normalize_price(raw: dict) -> dict:
    """
    Přijme surový záznam ceny a vrátí normalizovaný dict pro uložení do DB.

    Očekávaná pole v `raw`:
        price        – číslo
        currency     – kód měny (str)
        departure_date – date nebo str "YYYY-MM-DD"
        (volitelně) return_date, airline_detail, flight_numbers, stops, duration_minutes
    """
    from datetime import date

    price_orig = float(raw["price"])
    currency = raw.get("currency", "EUR")
    price_eur = to_eur(price_orig, currency)

    dep = raw["departure_date"]
    if isinstance(dep, str):
        from datetime import datetime
        dep = datetime.strptime(dep[:10], "%Y-%m-%d").date()

    ret = raw.get("return_date")
    if isinstance(ret, str) and ret:
        from datetime import datetime
        ret = datetime.strptime(ret[:10], "%Y-%m-%d").date()

    return {
        "price_eur": price_eur,
        "price_original": price_orig,
        "currency_original": currency.upper(),
        "departure_date": dep,
        "return_date": ret,
        "airline_detail": raw.get("airline_detail"),
        "flight_numbers": raw.get("flight_numbers"),
        "stops": int(raw.get("stops", 0)),
        "duration_minutes": raw.get("duration_minutes"),
        "departure_time": raw.get("departure_time"),
        "arrival_time": raw.get("arrival_time"),
    }


def normalize_many(raw_list: list[dict]) -> list[dict]:
    """Normalizuje seznam surových cen."""
    result = []
    for raw in raw_list:
        try:
            result.append(normalize_price(raw))
        except Exception as e:
            logger.error(f"Chyba při normalizaci záznamu {raw}: {e}")
    return result
