"""Receiving-hospital encounters: state machine, timeline, notes, orders and results."""

import json
import uuid
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import DATA_DIR
from app.core.db import utcnow
from app.core.errors import AppError
from app.models import (
    ClinicalNote,
    Encounter,
    EncounterEvent,
    InvestigationOrder,
    LabResult,
    Referral,
    TriageReport,
    User,
)
from app.models.enums import (
    CANCEL_ROLES,
    CANCELLABLE,
    ENCOUNTER_TRANSITIONS,
    EncounterState,
    ReferralStatus,
)
from app.realtime.broker import broker

ES = EncounterState
STATE_LABEL = {
    ES.registered: "Registered",
    ES.awaiting_nursing: "Waiting for nurse",
    ES.awaiting_doctor: "Waiting for doctor",
    ES.awaiting_investigation: "Waiting for tests",
    ES.results_ready: "Results ready",
    ES.awaiting_disposition: "Waiting for discharge / admission",
    ES.completed: "Completed",
    ES.cancelled: "Cancelled",
}
DISPOSITIONS = {"discharged", "admitted", "transferred", "left"}


@lru_cache
def investigations() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "investigations.json").read_text())
    return {t["code"]: t for t in data["tests"]}


def publish(enc: Encounter, event: str = "encounter.updated") -> None:
    broker.publish(f"facility:{enc.facility_id}", event,
                   {"encounter_id": enc.id, "state": enc.state, "patient_id": enc.patient_id})


async def log(db: AsyncSession, enc: Encounter, actor: User | None, kind: str, summary: str, *,
              from_state: str | None = None, to_state: str | None = None, details: dict | None = None) -> None:
    db.add(EncounterEvent(encounter_id=enc.id, actor_id=actor.id if actor else None, kind=kind, summary=summary[:300],
                          from_state=from_state, to_state=to_state, details=details))


async def _move(db: AsyncSession, enc: Encounter, to: str, actor: User | None, summary: str | None = None) -> None:
    frm = enc.state
    enc.state = to
    if to == ES.completed:
        enc.completed_at = utcnow()
    await log(db, enc, actor, "state", summary or f"{STATE_LABEL[frm]} → {STATE_LABEL[to]}", from_state=frm,
              to_state=to)


async def open_encounter(
    db: AsyncSession, *, facility_id: uuid.UUID, patient_id: uuid.UUID, actor: User,
    referral: Referral | None = None, emergency: bool = False, chief_complaint: str | None = None,
) -> Encounter:
    report = await db.get(TriageReport, referral.report_id) if referral else None
    emergency = emergency or bool(report and report.red_flag)
    enc = Encounter(
        facility_id=facility_id, patient_id=patient_id, referral_id=referral.id if referral else None,
        report_id=report.id if report else None, emergency=emergency, chief_complaint=chief_complaint,
        created_by=actor.id, state=ES.registered,
    )
    db.add(enc)
    await db.flush()
    how = "Arrived by referral" if referral else "Walk-in registered"
    await log(db, enc, actor, "state", how, to_state=ES.registered)
    # Emergency flag skips straight to the doctor.
    nxt = ES.awaiting_doctor if emergency else ES.awaiting_nursing
    await _move(db, enc, nxt, actor, "Emergency: straight to doctor" if emergency else "Sent to nursing")
    await audit(db, "encounter.open", actor_id=actor.id, subject_type="encounter", subject_id=enc.id,
                facility_id=facility_id, details={"emergency": emergency, "referral": bool(referral)})
    return enc


async def transition(db: AsyncSession, enc: Encounter, to: str, actor: User, *, disposition: str | None = None,
                     note: str | None = None, reason: str | None = None) -> None:
    if to == ES.cancelled:
        if enc.state not in CANCELLABLE or actor.role not in CANCEL_ROLES:
            raise AppError(403 if enc.state in CANCELLABLE else 409, "not_allowed", "Cannot cancel this encounter")
        if not (reason or "").strip():
            raise AppError(422, "reason_required", "A reason is required")
        enc.cancel_reason = reason.strip()
        await _move(db, enc, to, actor, f"Cancelled: {enc.cancel_reason}")
    else:
        roles = ENCOUNTER_TRANSITIONS.get((enc.state, to))
        if roles is None:
            raise AppError(409, "invalid_transition", f"Cannot go from {enc.state} to {to}")
        if actor.role not in roles:
            raise AppError(403, "forbidden", "Your role cannot do this step")
        if to == ES.awaiting_disposition:
            if disposition not in DISPOSITIONS:
                raise AppError(422, "disposition_required", "Choose discharged, admitted, transferred or left")
            signed = (await db.execute(select(ClinicalNote.id).where(
                ClinicalNote.encounter_id == enc.id, ClinicalNote.status == "signed"))).first()
            if not signed:
                raise AppError(409, "note_required", "Sign a clinical note before the disposition")
            enc.disposition = disposition
            enc.disposition_note = (note or "").strip() or None
            await _move(db, enc, to, actor, f"Disposition decided: {disposition}")
        else:
            await _move(db, enc, to, actor)
        if to == ES.completed and enc.referral_id:
            ref = await db.get(Referral, enc.referral_id)
            if ref and ref.status == ReferralStatus.arrived:
                ref.status = ReferralStatus.completed
                ref.completed_at = utcnow()
    await audit(db, f"encounter.{to}", actor_id=actor.id, subject_type="encounter", subject_id=enc.id,
                facility_id=enc.facility_id)


# ---------- notes ----------
async def save_note(db: AsyncSession, enc: Encounter, actor: User, body: str, note_id: uuid.UUID | None) -> ClinicalNote:
    body = body.strip()
    if not body:
        raise AppError(422, "validation_error", "Note is empty")
    if note_id:
        n = await db.get(ClinicalNote, note_id)
        if not n or n.encounter_id != enc.id:
            raise AppError(404, "not_found", "Note not found")
        if n.status == "signed":
            # Amendment: a new draft that supersedes the signed note; the signed one is kept.
            n = ClinicalNote(encounter_id=enc.id, author_id=actor.id, body=body, version=n.version + 1,
                             supersedes_id=n.id)
            db.add(n)
        else:
            if n.author_id != actor.id:
                raise AppError(403, "forbidden", "Only the author can edit a draft")
            n.body = body
    else:
        n = ClinicalNote(encounter_id=enc.id, author_id=actor.id, body=body)
        db.add(n)
    await db.flush()
    return n


async def sign_note(db: AsyncSession, enc: Encounter, actor: User, note_id: uuid.UUID) -> ClinicalNote:
    n = await db.get(ClinicalNote, note_id)
    if not n or n.encounter_id != enc.id:
        raise AppError(404, "not_found", "Note not found")
    if n.author_id != actor.id:
        raise AppError(403, "forbidden", "Only the author can sign")
    if n.status == "signed":
        raise AppError(409, "already_signed", "Already signed")
    n.status = "signed"
    n.signed_at = utcnow()
    await log(db, enc, actor, "note", f"Note v{n.version} signed")
    await audit(db, "note.sign", actor_id=actor.id, subject_type="note", subject_id=n.id, facility_id=enc.facility_id)
    return n


# ---------- orders ----------
async def place_orders(db: AsyncSession, enc: Encounter, actor: User, items: list[dict]) -> list[InvestigationOrder]:
    if enc.state not in (ES.awaiting_doctor, ES.results_ready, ES.awaiting_investigation):
        raise AppError(409, "invalid_state", "Orders can be placed while the patient is with the doctor")
    cat = investigations()
    created = []
    for it in items:
        t = cat.get(it["test_code"])
        if not t:
            raise AppError(422, "validation_error", f"Unknown test {it['test_code']}")
        o = InvestigationOrder(encounter_id=enc.id, facility_id=enc.facility_id, ordered_by=actor.id,
                               category=t["category"], test_code=t["code"], test_name=t["name"],
                               priority=it.get("priority", "routine"), clinical_note=it.get("note"))
        db.add(o)
        created.append(o)
    await db.flush()
    await log(db, enc, actor, "order", "Ordered: " + ", ".join(o.test_name for o in created))
    if enc.state != ES.awaiting_investigation:
        await _move(db, enc, ES.awaiting_investigation, actor)
    await audit(db, "order.create", actor_id=actor.id, subject_type="encounter", subject_id=enc.id,
                facility_id=enc.facility_id, details={"tests": [o.test_code for o in created]})
    return created


async def enter_result(db: AsyncSession, order: InvestigationOrder, actor: User, text: str, abnormal: bool) -> None:
    if order.status not in ("ordered", "resulted"):
        raise AppError(409, "invalid_state", f"Order is {order.status}")
    if not text.strip():
        raise AppError(422, "validation_error", "Result is empty")
    res = (await db.execute(select(LabResult).where(LabResult.order_id == order.id))).scalar_one_or_none()
    if res:
        res.result_text, res.abnormal, res.entered_by, res.entered_at = text.strip(), abnormal, actor.id, utcnow()
    else:
        db.add(LabResult(order_id=order.id, result_text=text.strip(), abnormal=abnormal, entered_by=actor.id))
    order.status = "resulted"
    enc = await db.get(Encounter, order.encounter_id)
    await log(db, enc, actor, "result", f"Result entered: {order.test_name}")
    await audit(db, "order.result", actor_id=actor.id, subject_type="order", subject_id=order.id,
                facility_id=order.facility_id)


async def verify_result(db: AsyncSession, order: InvestigationOrder, actor: User) -> Encounter:
    """Verification is a separate action. When every order is verified the encounter goes back to the doctor."""
    if order.status != "resulted":
        raise AppError(409, "invalid_state", "Enter the result before verifying")
    res = (await db.execute(select(LabResult).where(LabResult.order_id == order.id))).scalar_one()
    res.verified_by, res.verified_at = actor.id, utcnow()
    order.status = "verified"
    enc = await db.get(Encounter, order.encounter_id)
    assert enc is not None
    await log(db, enc, actor, "verify", f"Result verified: {order.test_name}")
    await db.flush()
    pending = (await db.execute(select(InvestigationOrder.id).where(
        InvestigationOrder.encounter_id == enc.id, InvestigationOrder.status.in_(["ordered", "resulted"])))).first()
    if not pending and enc.state == ES.awaiting_investigation:
        await _move(db, enc, ES.results_ready, actor, "All results verified → back to doctor")
    await audit(db, "order.verify", actor_id=actor.id, subject_type="order", subject_id=order.id,
                facility_id=order.facility_id)
    return enc
