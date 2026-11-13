"""Receiving hospital: reception, nursing, doctor, lab/radiology. Every query is scoped to the user's facility."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import ensure_same_facility, require_hospital_staff
from app.core.errors import AppError, Envelope, ok
from app.engines.triage.data import care_types, symptom_index
from app.engines.triage.red_flags import evaluate as eval_red_flags
from app.engines.triage.state import TriageState
from app.models import (
    ClinicalNote,
    Encounter,
    EncounterEvent,
    InvestigationOrder,
    LabResult,
    Patient,
    Referral,
    TriageReport,
    User,
    Vital,
)
from app.models.enums import CANCEL_ROLES, CANCELLABLE, ENCOUNTER_TRANSITIONS, EncounterState, Role
from app.schemas.encounter import (
    Allowed,
    EncounterListItem,
    EncounterOut,
    EncounterVitalsIn,
    LabQueueItem,
    NoteIn,
    NoteRow,
    OrderRow,
    OrdersIn,
    ReferralSummary,
    ResultIn,
    TestOption,
    TimelineRow,
    TransitionIn,
    VitalRow,
    WalkInIn,
    WalkInOut,
)
from app.schemas.referral import IncomingPatient, SymptomLine
from app.schemas.worker import VITAL_RANGES
from app.services import encounters as esvc
from app.services.patients import create_patient

router = APIRouter(prefix="/hospital", tags=["encounters"])
ES = EncounterState
any_staff = require_hospital_staff()
front_desk = require_hospital_staff(Role.receptionist, Role.nurse, Role.facility_admin)
clinical = require_hospital_staff(Role.nurse, Role.doctor)
doctor_only = require_hospital_staff(Role.doctor)
lab_only = require_hospital_staff(Role.lab, Role.radiology)
# Each department sees and handles only its own orders.
DEPARTMENT = {Role.lab: "lab", Role.radiology: "radiology"}


async def _scoped(db: AsyncSession, encounter_id: uuid.UUID, user: User) -> Encounter:
    enc = await db.get(Encounter, encounter_id)
    if not enc:
        raise AppError(404, "not_found", "Not found")
    ensure_same_facility(user, enc.facility_id)
    return enc


async def _names(db: AsyncSession, ids: set) -> dict[uuid.UUID, User]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: u for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars()}


def _patient_brief(p: Patient, report: TriageReport | None) -> IncomingPatient:
    ctx = (report.context if report else None) or {}
    return IncomingPatient(vitalis_id=p.vitalis_id, age_group=ctx.get("age_group") or p.age_group,
                           sex=ctx.get("sex") or p.sex, pregnant=bool(ctx.get("pregnant") or p.pregnant))


def _care_label(ct: str | None) -> str | None:
    return care_types()["care_types"].get(ct or "", {}).get("label")


def _urgent(kind: str, value: float) -> bool:
    return eval_red_flags(TriageState(vitals={kind: value})).fired


def _allowed(enc: Encounter, user: User) -> Allowed:
    active = enc.state not in (ES.completed, ES.cancelled)
    return Allowed(
        transitions=[to for (frm, to), roles in ENCOUNTER_TRANSITIONS.items() if frm == enc.state and user.role in roles],
        record_vitals=active and user.role in (Role.nurse, Role.doctor),
        write_notes=active and user.role == Role.doctor,
        order_tests=user.role == Role.doctor
        and enc.state in (ES.awaiting_doctor, ES.results_ready, ES.awaiting_investigation),
        cancel=enc.state in CANCELLABLE and user.role in CANCEL_ROLES,
    )


async def _order_rows(db: AsyncSession, orders: list[InvestigationOrder]) -> list[OrderRow]:
    results = {
        r.order_id: r
        for r in (await db.execute(select(LabResult).where(LabResult.order_id.in_([o.id for o in orders])))).scalars()
    } if orders else {}
    people = await _names(db, {o.ordered_by for o in orders} | {o.collected_by for o in orders if o.collected_by}
                          | {r.entered_by for r in results.values()} | {r.verified_by for r in results.values()})
    name = lambda i: people[i].full_name if i in people else None
    rows = []
    for o in orders:
        r = results.get(o.id)
        rows.append(OrderRow(
            id=o.id, category=o.category, test_code=o.test_code, test_name=o.test_name, priority=o.priority,
            clinical_note=o.clinical_note, status=o.status, ordered_by=name(o.ordered_by), created_at=o.created_at,
            collected_by=name(o.collected_by) if o.collected_by else None, collected_at=o.collected_at,
            result_text=r.result_text if r else None, values=r.values if r else None,
            abnormal=r.abnormal if r else None,
            entered_by=name(r.entered_by) if r else None, entered_at=r.entered_at if r else None,
            verified_by=name(r.verified_by) if r and r.verified_by else None,
            verified_at=r.verified_at if r else None,
        ))
    return rows


async def _detail(db: AsyncSession, enc: Encounter, user: User) -> EncounterOut:
    patient = await db.get(Patient, enc.patient_id)
    assert patient is not None
    report = await db.get(TriageReport, enc.report_id) if enc.report_id else None
    ref = await db.get(Referral, enc.referral_id) if enc.referral_id else None

    referral = None
    if ref and report:
        worker = await db.get(User, report.worker_id) if report.worker_id else None
        idx = symptom_index()
        referral = ReferralSummary(
            referral_id=ref.id, referred_by=worker.full_name if worker else None,
            red_flag_message=report.red_flag_message, care_type=report.care_type,
            care_label=_care_label(report.care_type),
            symptoms=[SymptomLine(code=s["code"], label=idx.get(s["code"], {}).get("labels", {}).get("en", s["code"]),
                                  region=s.get("region"), severity=s.get("severity"), onset=s.get("onset"))
                      for s in (report.answers or {}).get("symptoms", [])],
            sent_at=ref.created_at, arrived_at=ref.arrived_at,
        )

    # Vitals from this encounter plus the referring triage (the chemist's readings), oldest first.
    conds = [Vital.encounter_id == enc.id]
    if enc.report_id:
        conds.append(Vital.report_id == enc.report_id)
    vitals = (await db.execute(
        select(Vital).where(Vital.patient_id == enc.patient_id, or_(*conds)).order_by(Vital.measured_at)
    )).scalars().all()
    superseded = {v.corrected_from for v in vitals if v.corrected_from}

    notes = (await db.execute(select(ClinicalNote).where(ClinicalNote.encounter_id == enc.id)
                              .order_by(ClinicalNote.created_at))).scalars().all()
    # Drafts are private to their author.
    notes = [n for n in notes if n.status == "signed" or n.author_id == user.id]
    orders = (await db.execute(select(InvestigationOrder).where(InvestigationOrder.encounter_id == enc.id)
                               .order_by(InvestigationOrder.created_at))).scalars().all()
    events = (await db.execute(select(EncounterEvent).where(EncounterEvent.encounter_id == enc.id)
                               .order_by(EncounterEvent.at))).scalars().all()
    people = await _names(db, {v.entered_by for v in vitals} | {n.author_id for n in notes}
                          | {e.actor_id for e in events})

    return EncounterOut(
        id=enc.id, patient_id=enc.patient_id, state=enc.state, state_label=esvc.STATE_LABEL[ES(enc.state)], emergency=enc.emergency,
        chief_complaint=enc.chief_complaint, disposition=enc.disposition, disposition_note=enc.disposition_note,
        cancel_reason=enc.cancel_reason, created_at=enc.created_at, completed_at=enc.completed_at,
        patient=_patient_brief(patient, report), referral=referral,
        vitals=[VitalRow(id=v.id, kind=v.kind, value=v.value, unit=v.unit, source=v.source,
                         measured_at=v.measured_at,
                         entered_by=people[v.entered_by].full_name if v.entered_by in people else None,
                         corrected_from=v.corrected_from, superseded=v.id in superseded,
                         urgent=_urgent(v.kind, v.value)) for v in vitals],
        notes=[NoteRow(id=n.id, author_id=n.author_id, author=people[n.author_id].full_name if n.author_id in people
                       else "?", status=n.status, version=n.version, body=n.body, supersedes_id=n.supersedes_id,
                       created_at=n.created_at, signed_at=n.signed_at) for n in notes],
        orders=await _order_rows(db, list(orders)),
        timeline=[TimelineRow(at=e.at, actor=people[e.actor_id].full_name if e.actor_id in people else None,
                              actor_role=people[e.actor_id].role if e.actor_id in people else None,
                              kind=e.kind, summary=e.summary) for e in events],
        allowed=_allowed(enc, user),
    )


async def _respond(db: AsyncSession, enc: Encounter, user: User) -> EncounterOut:
    await db.commit()
    esvc.publish(enc)
    return await _detail(db, enc, user)


# ---------- lists ----------
@router.get("/encounters", response_model=Envelope[list[EncounterListItem]])
async def list_encounters(
    state: str | None = Query(None, max_length=64, description="comma-separated states; default = open"),
    user: User = Depends(any_staff), db: AsyncSession = Depends(get_db),
):
    q = select(Encounter).where(Encounter.facility_id == user.facility_id)
    if state:
        q = q.where(Encounter.state.in_(state.split(",")))
    else:
        q = q.where(Encounter.state.not_in([ES.completed, ES.cancelled]))
    rows = (await db.execute(q.order_by(Encounter.emergency.desc(), Encounter.created_at).limit(200))).scalars().all()
    counts = dict((await db.execute(
        select(InvestigationOrder.encounter_id, func.count()).where(
            InvestigationOrder.encounter_id.in_([e.id for e in rows]),
            InvestigationOrder.status.in_(esvc.OPEN_ORDER)).group_by(InvestigationOrder.encounter_id)
    )).all()) if rows else {}
    out = []
    for e in rows:
        p = await db.get(Patient, e.patient_id)
        r = await db.get(TriageReport, e.report_id) if e.report_id else None
        out.append(EncounterListItem(
            id=e.id, state=e.state, state_label=esvc.STATE_LABEL[ES(e.state)], emergency=e.emergency,
            patient=_patient_brief(p, r), care_label=_care_label(r.care_type if r else None),
            headline=(r.red_flag_message if r and r.red_flag_message else e.chief_complaint),
            created_at=e.created_at, updated_at=e.updated_at, open_orders=counts.get(e.id, 0),
        ))
    return ok(out)


@router.get("/tests", response_model=Envelope[list[TestOption]])
async def test_catalogue(_: User = Depends(any_staff)):
    return ok([TestOption.model_validate(t) for t in esvc.investigations().values()])


# ---------- reception ----------
@router.post("/encounters", response_model=Envelope[WalkInOut])
async def register_walk_in(body: WalkInIn, user: User = Depends(front_desk), db: AsyncSession = Depends(get_db)):
    patient, _key, recovery = await create_patient(db, phone=body.family_phone, age_group=body.age_group,
                                                   sex=body.sex, pregnant=body.pregnant)
    enc = await esvc.open_encounter(db, facility_id=user.facility_id, patient_id=patient.id, actor=user,
                                    emergency=body.emergency, chief_complaint=body.chief_complaint.strip())
    await db.commit()
    esvc.publish(enc, "encounter.new")
    return ok(WalkInOut(encounter_id=enc.id, vitalis_id=patient.vitalis_id, recovery_code=recovery))


@router.get("/encounters/{encounter_id}", response_model=Envelope[EncounterOut])
async def get_encounter(encounter_id: uuid.UUID, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    out = await _detail(db, enc, user)
    await audit(db, "encounter.view", actor_id=user.id, subject_type="encounter", subject_id=enc.id,
                facility_id=user.facility_id)
    await db.commit()
    return ok(out)


@router.post("/encounters/{encounter_id}/transition", response_model=Envelope[EncounterOut])
async def move(encounter_id: uuid.UUID, body: TransitionIn, user: User = Depends(any_staff),
               db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    await esvc.transition(db, enc, body.to, user, disposition=body.disposition, note=body.note, reason=body.reason)
    return ok(await _respond(db, enc, user))


# ---------- nursing ----------
@router.post("/encounters/{encounter_id}/vitals", response_model=Envelope[EncounterOut])
async def record_vitals(encounter_id: uuid.UUID, body: EncounterVitalsIn, user: User = Depends(clinical),
                        db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    if enc.state in (ES.completed, ES.cancelled):
        raise AppError(409, "invalid_state", "Encounter is closed")
    original = None
    if body.corrected_from:
        if len(body.readings) != 1 or not (body.correction_reason or "").strip():
            raise AppError(422, "validation_error", "A correction replaces one reading and needs a reason")
        original = await db.get(Vital, body.corrected_from)
        if not original or original.patient_id != enc.patient_id or original.kind != body.readings[0].kind:
            raise AppError(404, "not_found", "Reading to correct not found")
    now = utcnow()
    urgent = []
    for r in body.readings:
        lo, hi, unit = VITAL_RANGES[r.kind]
        if not lo <= r.value <= hi:
            raise AppError(422, "vital_out_of_range", f"{r.kind} must be between {lo:g} and {hi:g} {unit}")
        db.add(Vital(patient_id=enc.patient_id, encounter_id=enc.id, source="nurse", kind=r.kind, value=r.value,
                     unit=unit, measured_at=r.measured_at or now, entered_by=user.id,
                     corrected_from=original.id if original else None))
        if _urgent(r.kind, r.value):
            urgent.append(r.kind)
    if original:
        summary = f"Corrected {original.kind}: {original.value:g} → {body.readings[0].value:g} ({body.correction_reason})"
        await esvc.log(db, enc, user, "correction", summary)
        await audit(db, "vitals.correct", actor_id=user.id, subject_type="vital", subject_id=original.id,
                    facility_id=enc.facility_id, details={"reason": body.correction_reason})
    else:
        await esvc.log(db, enc, user, "vitals", "Vitals recorded: " + ", ".join(r.kind for r in body.readings)
                       + (f" (URGENT: {', '.join(urgent)})" if urgent else ""))
    return ok(await _respond(db, enc, user))


# ---------- doctor ----------
@router.post("/encounters/{encounter_id}/notes", response_model=Envelope[EncounterOut])
async def write_note(encounter_id: uuid.UUID, body: NoteIn, user: User = Depends(doctor_only),
                     db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    if enc.state in (ES.completed, ES.cancelled):
        raise AppError(409, "invalid_state", "Encounter is closed")
    await esvc.save_note(db, enc, user, body.body, body.note_id)
    return ok(await _respond(db, enc, user))


@router.post("/encounters/{encounter_id}/notes/{note_id}/sign", response_model=Envelope[EncounterOut])
async def sign(encounter_id: uuid.UUID, note_id: uuid.UUID, user: User = Depends(doctor_only),
               db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    await esvc.sign_note(db, enc, user, note_id)
    return ok(await _respond(db, enc, user))


@router.post("/encounters/{encounter_id}/orders", response_model=Envelope[EncounterOut])
async def order(encounter_id: uuid.UUID, body: OrdersIn, user: User = Depends(doctor_only),
                db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    await esvc.place_orders(db, enc, user, [i.model_dump() for i in body.items])
    return ok(await _respond(db, enc, user))


# ---------- lab / radiology ----------
@router.get("/lab/queue", response_model=Envelope[list[LabQueueItem]])
async def lab_queue(user: User = Depends(lab_only), db: AsyncSession = Depends(get_db)):
    orders = (await db.execute(
        select(InvestigationOrder).where(InvestigationOrder.facility_id == user.facility_id,
                                         InvestigationOrder.category == DEPARTMENT[user.role],
                                         InvestigationOrder.status.in_(esvc.OPEN_ORDER))
        .order_by(InvestigationOrder.priority.desc(), InvestigationOrder.created_at)
    )).scalars().all()
    rows = await _order_rows(db, list(orders))
    out = []
    for o, row in zip(orders, rows, strict=True):
        enc = await db.get(Encounter, o.encounter_id)
        p = await db.get(Patient, enc.patient_id)
        r = await db.get(TriageReport, enc.report_id) if enc.report_id else None
        out.append(LabQueueItem(order=row, encounter_id=enc.id, vitalis_id=p.vitalis_id, emergency=enc.emergency,
                                patient=_patient_brief(p, r)))
    return ok(out)


async def _scoped_order(db: AsyncSession, order_id: uuid.UUID, user: User) -> InvestigationOrder:
    o = await db.get(InvestigationOrder, order_id)
    if not o:
        raise AppError(404, "not_found", "Not found")
    ensure_same_facility(user, o.facility_id)
    if user.role in DEPARTMENT and o.category != DEPARTMENT[user.role]:
        raise AppError(404, "not_found", "Not found")
    return o


@router.post("/orders/{order_id}/collect", response_model=Envelope[OrderRow])
async def collect(order_id: uuid.UUID, user: User = Depends(lab_only), db: AsyncSession = Depends(get_db)):
    o = await _scoped_order(db, order_id, user)
    await esvc.collect_sample(db, o, user)
    await db.commit()
    enc = await db.get(Encounter, o.encounter_id)
    esvc.publish(enc)
    return ok((await _order_rows(db, [o]))[0])


@router.post("/orders/{order_id}/result", response_model=Envelope[OrderRow])
async def result(order_id: uuid.UUID, body: ResultIn, user: User = Depends(lab_only),
                 db: AsyncSession = Depends(get_db)):
    o = await _scoped_order(db, order_id, user)
    values = {k: v.model_dump() for k, v in (body.values or {}).items()} or None
    await esvc.enter_result(db, o, user, body.result_text, body.abnormal, values)
    await db.commit()
    enc = await db.get(Encounter, o.encounter_id)
    esvc.publish(enc)
    return ok((await _order_rows(db, [o]))[0])


@router.post("/orders/{order_id}/verify", response_model=Envelope[OrderRow])
async def verify(order_id: uuid.UUID, user: User = Depends(lab_only), db: AsyncSession = Depends(get_db)):
    o = await _scoped_order(db, order_id, user)
    enc = await esvc.verify_result(db, o, user)
    await db.commit()
    esvc.publish(enc)
    return ok((await _order_rows(db, [o]))[0])
