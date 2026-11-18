"""Offline bundle: everything the app needs to triage and find hospitals with no signal.

The phone saves it when online (it is public: the same rules and verified hospitals anyone can see in the app) and
runs the same red-flag rules and matching locally when the network is gone. Hospitals are not alerted until the
phone is back online, and the app says so.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.errors import ok
from app.engines.matching.engine import CONFIRMED_H, NEARBY_KM, STALE_H
from app.engines.matching.loader import load_snapshots
from app.engines.triage.data import care_types, red_flags, symptoms
from app.schemas.triage import Taxonomy
from app.services import triage as svc

router = APIRouter(prefix="/offline", tags=["offline"])


@router.get("/bundle")
async def bundle(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=300"
    ct = care_types()
    snaps = await load_snapshots(db)
    return ok({
        "generated_at": utcnow().isoformat(),
        "taxonomy": Taxonomy.model_validate({**symptoms(), "lgas": svc.lgas()["lgas"]}).model_dump(),
        "emergencies": [
            {"code": e["code"], "context": e.get("context", {}),
             "symptoms": [{k: v for k, v in s.items() if k in ("code", "region", "severity", "onset")}
                          for s in e.get("symptoms", [])]}
            for e in symptoms()["emergencies"]
        ],
        "red_flags": {"version": red_flags()["version"], "rules": red_flags()["rules"]},
        "care": {
            "version": ct["version"],
            "services": {s["code"]: s["name"] for s in ct["services"]},
            "care_types": ct["care_types"],
            "context_overrides": ct["context_overrides"],
            "region_defaults": ct["region_defaults"],
            "action_rules": ct["action_rules"],
        },
        "matching": {"nearby_km": NEARBY_KM, "confirmed_h": CONFIRMED_H, "stale_h": STALE_H,
                     "speed_kmh": get_settings().city_speed_kmh},
        "facilities": [
            {"id": str(f.id), "name": f.name, "lga": f.lga, "type": f.type, "lat": f.lat, "lng": f.lng,
             "phone": f.phone, "accepts_nhia": f.accepts_nhia, "free_maternal_care": f.free_maternal_care,
             "services": {c: {"status": s.status,
                              "last_confirmed_at": s.last_confirmed_at.isoformat() if s.last_confirmed_at else None}
                          for c, s in f.services.items()}}
            for f in snaps
        ],
    })
