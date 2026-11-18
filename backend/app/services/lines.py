"""Numbers people can call: the national emergency line and the state ambulance for where they are."""

import json
from functools import lru_cache

from app.core.config import DATA_DIR
from app.engines.matching.engine import haversine_km
from app.schemas.triage import Line


@lru_cache
def _data() -> dict:
    return json.loads((DATA_DIR / "emergency_lines.json").read_text())


@lru_cache
def _lgas() -> list[dict]:
    return json.loads((DATA_DIR / "lgas.json").read_text())["lgas"]


def national() -> Line:
    return Line(**_data()["national"])


def state_at(lat: float | None, lng: float | None, lga: str | None = None) -> str | None:
    """The state of the named LGA, or of the nearest known LGA within max_km."""
    rows = _lgas()
    if lga:
        row = next((r for r in rows if r["name"] == lga), None)
        if row:
            return row.get("state")
    if lat is None or lng is None:
        return None
    best = min(rows, key=lambda r: haversine_km(lat, lng, r["lat"], r["lng"]))
    return best.get("state") if haversine_km(lat, lng, best["lat"], best["lng"]) <= _data()["max_km"] else None


def ambulance(lat: float | None, lng: float | None, lga: str | None = None) -> Line | None:
    state = state_at(lat, lng, lga)
    row = _data()["ambulances"].get(state or "")
    return Line(**row) if row else None


def ambulances() -> list[Line]:
    return [Line(**v) for v in _data()["ambulances"].values()]


def call_text(lat: float | None, lng: float | None, lga: str | None = None) -> str:
    """Short SMS/USSD line, e.g. 'Ambulance: 08112000033. Emergency: 112.'"""
    amb = ambulance(lat, lng, lga)
    return (f"Ambulance: {amb.number}. " if amb else "") + f"Emergency: {national().number}."


def bundle() -> dict:
    """For the offline bundle: the phone picks the ambulance the same way with no signal."""
    d = _data()
    return {"national": d["national"], "max_km": d["max_km"], "ambulances": d["ambulances"],
            "lgas": [{k: r.get(k) for k in ("name", "lat", "lng", "state")} for r in _lgas()]}
