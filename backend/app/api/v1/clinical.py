"""Doctor tools: the patient's record (allergies, conditions, medicines, family), VITALIS AI drafts, safe prescribing."""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.encounters import _scoped, any_staff, clinical, doctor_only
from app.core.audit import audit
from app.core.db import get_db, utcnow
from app.core.deps import ensure_same_facility
from app.core.errors import AppError, Envelope, ok
from app.engines.clinical import medication_safety as ms
from app.models import (
    AIDraft,
    ClinicalNote,
    Encounter,
    Facility,
    Patient,
    PatientHistoryEntry,
    Prescription,
    TriageReport,
    User,
)
from app.services import clinical_ai, records
from app.services import encounters as esvc

router = APIRouter(prefix="/hospital", tags=["clinical"])
HistoryKind = Literal["allergy", "condition", "medication", "family"]


class HistoryRow(BaseModel):
    id: uuid.UUID
    kind: str
    text: str
    detail: str | None
    onset_age: int | None
    source: str
    recorded_at: datetime
    here: bool


class PrescriptionRow(BaseModel):
    id: uuid.UUID
    drug: str
    dose: str
    status: str
    safety: dict
    override_reason: str | None
    prescribed_by: str | None
    created_at: datetime


class RecordOut(BaseModel):
    history: list[HistoryRow]
    prescriptions: list[PrescriptionRow]
    hidden_from_other_hospitals: int  # entries recorded elsewhere that need the patient's consent


class HistoryIn(BaseModel):
    kind: HistoryKind
    text: str = Field(min_length=2, max_length=200)
    detail: str | None = Field(default=None, max_length=200)
    onset_age: int | None = Field(default=None, ge=0, le=120)


class SafetyIn(BaseModel):
    drug: str = Field(min_length=2, max_length=120)


class PrescribeIn(BaseModel):
    drug: str = Field(min_length=2, max_length=120)
    dose: str = Field(min_length=2, max_length=120)
    override_reason: str | None = Field(default=None, max_length=500)


class DraftOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    rationale: str | None
    narrative_provider: str
    output: dict


class DraftDecisionIn(BaseModel):
    action: Literal["accepted", "edited", "rejected"]
    rationale: str | None = Field(default=None, max_length=1000)


async def _record(db: AsyncSession, enc: Encounter) -> RecordOut:
    consent = await records.active_consent(db, enc.patient_id, enc.facility_id)
    rows = (await db.execute(
        select(PatientHistoryEntry, Facility.name).outerjoin(Facility, Facility.id == PatientHistoryEntry.facility_id)
        .where(records.history_filter(enc.patient_id, enc.facility_id, consent))
        .order_by(PatientHistoryEntry.kind, PatientHistoryEntry.recorded_at)
    )).all()
    hidden = 0 if consent else await records.hidden_history_count(db, enc.patient_id, enc.facility_id)
    rx = (await db.execute(select(Prescription).where(Prescription.encounter_id == enc.id)
                           .order_by(Prescription.created_at))).scalars().all()
    users = {u.id: u.full_name for u in (await db.execute(
        select(User).where(User.id.in_({p.prescribed_by for p in rx})))).scalars()} if rx else {}
    return RecordOut(
        history=[HistoryRow(id=h.id, kind=h.kind, text=h.text, detail=h.detail, onset_age=h.onset_age,
                            source=(fac or "Patient-reported").replace(" (Demo)", ""), recorded_at=h.recorded_at,
                            here=h.facility_id == enc.facility_id) for h, fac in rows],
        prescriptions=[PrescriptionRow(id=p.id, drug=p.drug, dose=p.dose, status=p.status, safety=p.safety,
                                       override_reason=p.override_reason, prescribed_by=users.get(p.prescribed_by),
                                       created_at=p.created_at) for p in rx],
        hidden_from_other_hospitals=hidden,
    )


@router.get("/encounters/{encounter_id}/record", response_model=Envelope[RecordOut])
async def record(encounter_id: uuid.UUID, user: User = Depends(any_staff), db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    out = await _record(db, enc)
    await audit(db, "record.view", actor_id=user.id, subject_type="patient", subject_id=enc.patient_id,
                facility_id=user.facility_id)
    await db.commit()
    return ok(out)


@router.post("/encounters/{encounter_id}/history", response_model=Envelope[RecordOut])
async def add_history(encounter_id: uuid.UUID, body: HistoryIn, user: User = Depends(clinical),
                      db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    db.add(PatientHistoryEntry(patient_id=enc.patient_id, kind=body.kind, text=body.text.strip(),
                               detail=(body.detail or "").strip() or None, onset_age=body.onset_age,
                               facility_id=enc.facility_id, recorded_by=user.id))
    await esvc.log(db, enc, user, "record", f"Added {body.kind}: {body.text.strip()}")
    await audit(db, "record.add", actor_id=user.id, subject_type="patient", subject_id=enc.patient_id,
                facility_id=user.facility_id, details={"kind": body.kind})
    await db.commit()
    return ok(await _record(db, enc))


async def _safety(db: AsyncSession, enc: Encounter, drug: str) -> ms.SafetyResult:
    hist = await clinical_ai.history_items(db, enc.patient_id, enc.facility_id)
    report = await db.get(TriageReport, enc.report_id) if enc.report_id else None
    patient = await db.get(Patient, enc.patient_id)
    pregnant = bool((report.context or {}).get("pregnant")) if report else False
    pregnant = pregnant or bool(patient and patient.pregnant)
    return ms.check(drug, hist["allergy"], hist["medication"], hist["condition"], pregnant)


@router.post("/encounters/{encounter_id}/prescriptions/check", response_model=Envelope[dict])
async def check_safety(encounter_id: uuid.UUID, body: SafetyIn, user: User = Depends(doctor_only),
                       db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    return ok((await _safety(db, enc, body.drug)).as_dict())


@router.post("/encounters/{encounter_id}/prescriptions", response_model=Envelope[RecordOut])
async def prescribe(encounter_id: uuid.UUID, body: PrescribeIn, user: User = Depends(doctor_only),
                    db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    if enc.state in ("completed", "cancelled"):
        raise AppError(409, "invalid_state", "Encounter is closed")
    res = await _safety(db, enc, body.drug)
    reason = (body.override_reason or "").strip() or None
    if res.verdict == "avoid" and not reason:
        raise AppError(409, "safety_conflict", "This medicine conflicts with the patient's record", res.as_dict())
    db.add(Prescription(encounter_id=enc.id, patient_id=enc.patient_id, prescribed_by=user.id, drug=body.drug.strip(),
                        dose=body.dose.strip(), safety=res.as_dict(), override_reason=reason))
    # It becomes a current medicine on the patient's record, so the next hospital's checks see it.
    db.add(PatientHistoryEntry(patient_id=enc.patient_id, kind="medication", text=body.drug.strip(),
                               detail=body.dose.strip(), facility_id=enc.facility_id, recorded_by=user.id))
    await esvc.log(db, enc, user, "prescription",
                   f"Prescribed {body.drug.strip()} ({body.dose.strip()})" + (" — safety override" if reason else ""))
    await audit(db, "prescription.override" if reason and res.verdict == "avoid" else "prescription.create",
                actor_id=user.id, subject_type="encounter", subject_id=enc.id, facility_id=user.facility_id,
                details={"drug": body.drug.strip(), "verdict": res.verdict, "override_reason": reason})
    await db.commit()
    esvc.publish(enc)
    return ok(await _record(db, enc))


def _draft_out(d: AIDraft) -> DraftOut:
    return DraftOut(id=d.id, created_at=d.created_at, action=d.action, rationale=d.rationale,
                    narrative_provider=d.narrative_provider, output=d.output)


@router.post("/encounters/{encounter_id}/ai-draft", response_model=Envelope[DraftOut])
async def run_ai(encounter_id: uuid.UUID, user: User = Depends(doctor_only), db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    draft = await clinical_ai.run_for_encounter(db, enc, user)
    await esvc.log(db, enc, user, "ai", "VITALIS AI assessment generated (pending review)")
    await db.commit()
    return ok(_draft_out(draft))


@router.get("/encounters/{encounter_id}/ai-draft", response_model=Envelope[DraftOut | None])
async def latest_ai(encounter_id: uuid.UUID, user: User = Depends(doctor_only), db: AsyncSession = Depends(get_db)):
    enc = await _scoped(db, encounter_id, user)
    d = (await db.execute(select(AIDraft).where(AIDraft.encounter_id == enc.id)
                          .order_by(AIDraft.created_at.desc()).limit(1))).scalar_one_or_none()
    return ok(_draft_out(d) if d else None)


@router.patch("/ai-drafts/{draft_id}", response_model=Envelope[DraftOut])
async def decide_ai(draft_id: uuid.UUID, body: DraftDecisionIn, user: User = Depends(doctor_only),
                    db: AsyncSession = Depends(get_db)):
    d = await db.get(AIDraft, draft_id)
    if not d:
        raise AppError(404, "not_found", "Not found")
    enc = await db.get(Encounter, d.encounter_id)
    ensure_same_facility(user, enc.facility_id if enc else None)
    if d.action != "pending":
        raise AppError(409, "already_reviewed", "This draft was already reviewed")
    if body.action == "rejected" and not (body.rationale or "").strip():
        raise AppError(422, "reason_required", "Say why you rejected it (kept in the audit log)")
    d.action, d.action_by, d.action_at = body.action, user.id, utcnow()
    d.rationale = (body.rationale or "").strip() or None
    if body.action in ("accepted", "edited"):
        # Only the doctor's signed note becomes the record: accepting puts the draft text into their draft note.
        text = clinical_ai.draft_note_text(d.output)
        mine = (await db.execute(select(ClinicalNote).where(
            ClinicalNote.encounter_id == enc.id, ClinicalNote.author_id == user.id, ClinicalNote.status == "draft"
        ))).scalars().first()
        if mine:
            mine.body = f"{mine.body}\n\n{text}"
        else:
            db.add(ClinicalNote(encounter_id=enc.id, author_id=user.id, body=text))
    await esvc.log(db, enc, user, "ai", f"VITALIS AI assessment {body.action}")
    await audit(db, f"ai.draft.{body.action}", actor_id=user.id, subject_type="ai_draft", subject_id=d.id,
                facility_id=user.facility_id, details={"rationale": d.rationale} if d.rationale else None)
    await db.commit()
    esvc.publish(enc)
    return ok(_draft_out(d))
