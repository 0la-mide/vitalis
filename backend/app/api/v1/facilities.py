from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.errors import Envelope, ok
from app.engines.matching.engine import match
from app.engines.matching.loader import load_snapshots
from app.schemas.triage import HospitalCard

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("", response_model=Envelope[list[HospitalCard]])
async def list_facilities(
    care_type: str | None = Query(default=None, max_length=32),
    lat: float = Query(default=7.1475, ge=-90, le=90),
    lng: float = Query(default=3.3619, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    """Verified facilities only, ranked for a care type."""
    res = match(await load_snapshots(db), care_type, lat, lng, utcnow(), get_settings().city_speed_kmh, limit=50)
    return ok(
        [
            HospitalCard(
                facility_id=x.facility_id, name=x.name, lga=x.lga, lat=x.lat, lng=x.lng, phone=x.phone,
                distance_km=x.distance_km, eta_minutes=x.eta_minutes, score=x.score, freshness=x.freshness,
                last_confirmed_at=x.last_confirmed_at, ready_now=x.ready_now, reasons=x.reasons,
                warnings=x.warnings,
            )
            for x in res.matches
        ]
    )
