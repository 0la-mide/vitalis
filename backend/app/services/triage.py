"""Triage pipeline. Order on every tap: red-flag rules -> disease model -> care type -> matching."""

import json
import uuid
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import DATA_DIR, get_settings
from app.core.db import utcnow
from app.core.errors import AppError
from app.engines.matching.engine import MatchResult, match
from app.engines.matching.loader import load_snapshots
from app.engines.model_client import client as model_client
from app.engines.triage import care, red_flags
from app.engines.triage.data import region_codes, symptom_index, symptoms
from app.engines.triage.state import TriageState
from app.models import FacilityAlert, ModelPrediction, SymptomTap, TriageReport, Vital
from app.models.enums import TriageStatus
from app.realtime.broker import broker

HEADS_UP_COUNT = 3
VALID_AGE = {"under5", "child", "teen", "adult", "elderly"}
VALID_SEX = {"female", "male", "unknown"}
VALID_ONSET = {"now", "today", "days", "week"}


@lru_cache
def lgas() -> dict:
    return json.loads((DATA_DIR / "lgas.json").read_text())


def lga_centroid(name: str | None) -> tuple[float, float, str]:
    data = lgas()
    for row in data["lgas"]:
        if row["name"] == name:
            return row["lat"], row["lng"], row["name"]
    d = next(r for r in data["lgas"] if r["name"] == data["default"])
    return d["lat"], d["lng"], d["name"]


def report_location(r: TriageReport) -> tuple[float, float, bool]:
    """(lat, lng, approximate)."""
    if r.lat is not None and r.lng is not None:
        return r.lat, r.lng, False
    lat, lng, _ = lga_centroid(r.lga)
    return lat, lng, True


@dataclass
class Evaluation:
    report: TriageReport
    rf: red_flags.RedFlagResult
    care_type: str | None
    care_source: str
    action_level: str | None
    matches: MatchResult
    model_ok: bool
    heads_up_sent: bool
    approx_location: bool


# ---------- applying taps ----------
def _emergency(code: str) -> dict:
    for e in symptoms()["emergencies"]:
        if e["code"] == code:
            return e
    raise AppError(422, "validation_error", f"Unknown emergency {code}")


def _add_symptom(answers: dict, item: dict) -> None:
    syms = answers.setdefault("symptoms", [])
    for s in syms:
        if s["code"] == item["code"]:
            s.update({k: v for k, v in item.items() if v is not None})
            return
    syms.append(item)


def apply_tap(r: TriageReport, tap: dict) -> None:
    kind = tap.get("kind")
    ctx = dict(r.context or {})
    ans = dict(r.answers or {})
    ans.setdefault("symptoms", [])
    ans.setdefault("regions", [])

    if kind == "emergency":
        e = _emergency(tap["code"])
        r.entry = e["code"]
        ctx.update(e["context"])
        for s in e["symptoms"]:
            _add_symptom(ans, dict(s))
    elif kind == "context":
        if "age_group" in tap:
            if tap["age_group"] not in VALID_AGE:
                raise AppError(422, "validation_error", "Invalid age group")
            ctx["age_group"] = tap["age_group"]
        if "sex" in tap:
            if tap["sex"] not in VALID_SEX:
                raise AppError(422, "validation_error", "Invalid sex")
            ctx["sex"] = tap["sex"]
        if "pregnant" in tap:
            ctx["pregnant"] = bool(tap["pregnant"])
            if ctx["pregnant"]:
                ctx["sex"] = "female"
        if "who" in tap:
            ctx["who"] = str(tap["who"])[:16]
    elif kind == "region":
        region = tap.get("region")
        if region not in region_codes():
            raise AppError(422, "validation_error", "Invalid region")
        if region not in ans["regions"]:
            ans["regions"].append(region)
    elif kind == "symptom":
        code = tap.get("code")
        if code not in symptom_index():
            raise AppError(422, "validation_error", "Invalid symptom")
        if tap.get("selected", True):
            _add_symptom(ans, {"code": code, "region": tap.get("region")})
        else:
            ans["symptoms"] = [s for s in ans["symptoms"] if s["code"] != code]
    elif kind == "severity":
        v = int(tap.get("value", 0))
        if not 1 <= v <= 5:
            raise AppError(422, "validation_error", "Invalid severity")
        ans["severity"] = v
        for s in ans["symptoms"]:
            s["severity"] = v
    elif kind == "onset":
        v = tap.get("value")
        if v not in VALID_ONSET:
            raise AppError(422, "validation_error", "Invalid onset")
        ans["onset"] = v
        for s in ans["symptoms"]:
            s["onset"] = v
    elif kind == "location":
        if tap.get("lat") is not None and tap.get("lng") is not None:
            lat, lng = float(tap["lat"]), float(tap["lng"])
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise AppError(422, "validation_error", "Invalid coordinates")
            r.lat, r.lng = lat, lng
        if tap.get("lga"):
            _, _, name = lga_centroid(tap["lga"])
            r.lga = name
    else:
        raise AppError(422, "validation_error", f"Unknown tap kind {kind}")

    r.context = ctx
    r.answers = ans
    flag_modified(r, "context")
    flag_modified(r, "answers")


# ---------- evaluating ----------
async def _latest_vitals(db: AsyncSession, r: TriageReport) -> dict[str, float]:
    rows = (
        await db.execute(
            select(Vital).where(Vital.report_id == r.id).order_by(Vital.measured_at.asc())
        )
    ).scalars()
    return {v.kind: v.value for v in rows}


async def evaluate(db: AsyncSession, r: TriageReport, *, call_model: bool = True) -> Evaluation:
    vitals = await _latest_vitals(db, r)
    st = TriageState.from_report(r.context or {}, r.answers or {}, vitals)

    # 1. Red flags: deterministic, local, never waits on the network.
    rf = red_flags.evaluate(st)
    r.rules_version = rf.rules_version
    first_fire = rf.fired and not r.red_flag
    r.red_flag = rf.fired
    r.red_flag_codes = [h.rule_id for h in rf.hits]
    r.red_flag_message = rf.primary.message if rf.primary else None
    if rf.fired and r.status == TriageStatus.open:
        r.status = TriageStatus.emergency

    # 2. Disease model (skipped once a red flag has fired: we stop asking and act).
    predictions: list[dict] = []
    model_ok = False
    if not call_model and st.symptoms and not rf.fired:
        # Re-evaluations without a model call (vitals, reads) keep the latest successful prediction.
        last = (
            await db.execute(
                select(ModelPrediction)
                .where(ModelPrediction.report_id == r.id, ModelPrediction.ok.is_(True))
                .order_by(ModelPrediction.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last and last.output:
            predictions = last.output.get("predictions", [])
    if call_model and st.symptoms and not rf.fired:
        res = await model_client.predict(st)
        model_ok = res.ok
        predictions = res.predictions
        db.add(
            ModelPrediction(
                report_id=r.id,
                model_version=res.model_version,
                ok=res.ok,
                latency_ms=res.latency_ms,
                error=res.error,
                input=res.request,
                output={"predictions": res.predictions} if res.ok else None,
            )
        )

    # 3. Care type + plain action.
    care_type, source = care.care_type_for(st, rf, predictions)
    r.care_type = care_type
    r.action_level = care.action_level_for(st, rf, care_type)

    # 4. Matching.
    lat, lng, approx = report_location(r)
    snaps = await load_snapshots(db, r.id)
    result = match(snaps, care_type, lat, lng, utcnow(), get_settings().city_speed_kmh)

    heads_up = False
    if first_fire and r.heads_up_sent_at is None:
        heads_up = await send_heads_up(db, r, result)

    return Evaluation(r, rf, care_type, source, r.action_level, result, model_ok, heads_up, approx)


async def send_heads_up(db: AsyncSession, r: TriageReport, result: MatchResult) -> bool:
    top = result.matches[:HEADS_UP_COUNT]
    if not top:
        return False
    r.heads_up_sent_at = utcnow()
    for m in top:
        alert = FacilityAlert(
            report_id=r.id,
            facility_id=m.facility_id,
            care_type=r.care_type,
            message=r.red_flag_message,
        )
        db.add(alert)
        await db.flush()
        broker.publish(
            f"facility:{m.facility_id}",
            "alert.new",
            {
                "alert_id": alert.id,
                "report_id": r.id,
                "care_type": r.care_type,
                "distance_km": m.distance_km,
                "eta_minutes": m.eta_minutes,
            },
        )
    return True


async def record_taps(db: AsyncSession, r: TriageReport, taps: list[dict]) -> None:
    seq = (
        await db.execute(select(func.coalesce(func.max(SymptomTap.seq), 0)).where(SymptomTap.report_id == r.id))
    ).scalar_one()
    for t in taps:
        apply_tap(r, t)
        seq += 1
        db.add(SymptomTap(report_id=r.id, seq=seq, kind=str(t.get("kind"))[:24], payload=t))


async def get_report_for_patient(db: AsyncSession, report_id: uuid.UUID, patient_id: uuid.UUID) -> TriageReport:
    r = await db.get(TriageReport, report_id)
    if not r or r.patient_id != patient_id:
        raise AppError(404, "not_found", "Triage report not found")
    return r
