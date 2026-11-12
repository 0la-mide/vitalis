"""The patient's record across the network, and who may see which part of it.

Rules
- A hospital always sees what it recorded itself, plus allergies from anywhere (safety-critical for treatment).
- Visits, vitals, results, notes, medicines and other history from OTHER hospitals need an active consent:
  given by the patient through a QR code (10-minute, single-use), after a referral ("share with this hospital"),
  or by tapping Allow on an access request. Consents last 24 hours and can be revoked at any time.
- Every view of another hospital's data is audited; the patient sees who looked.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.models import (
    ClinicalNote,
    Consent,
    Encounter,
    Facility,
    InvestigationOrder,
    LabResult,
    PatientHistoryEntry,
    Prescription,
    Referral,
    TriageReport,
    Vital,
)

CONSENT_HOURS = 24
QR_MINUTES = 10


async def active_consent(db: AsyncSession, patient_id: uuid.UUID, facility_id: uuid.UUID) -> Consent | None:
    now = utcnow()
    return (await db.execute(
        select(Consent).where(
            Consent.patient_id == patient_id,
            Consent.activated_at.is_not(None),
            Consent.revoked_at.is_(None),
            Consent.expires_at > now,
            or_(Consent.facility_id == facility_id, Consent.activated_facility_id == facility_id),
        ).order_by(Consent.scope.asc(), Consent.expires_at.desc()).limit(1)  # "full" sorts before "summary"
    )).scalar_one_or_none()


def new_consent(patient_id: uuid.UUID, facility_id: uuid.UUID | None, via: str, scope: str = "full",
                purpose: str | None = None, activate: bool = True) -> Consent:
    now = utcnow()
    return Consent(patient_id=patient_id, facility_id=facility_id, via=via, scope=scope, purpose=purpose,
                   created_at=now, expires_at=now + timedelta(hours=CONSENT_HOURS),
                   activated_at=now if activate else None, activated_facility_id=facility_id if activate else None)


async def visible_encounter_ids(db: AsyncSession, patient_id: uuid.UUID, facility_id: uuid.UUID) -> tuple[list, Consent | None]:
    consent = await active_consent(db, patient_id, facility_id)
    q = select(Encounter.id).where(Encounter.patient_id == patient_id)
    if not (consent and consent.scope == "full"):
        q = q.where(Encounter.facility_id == facility_id)
    return list((await db.execute(q)).scalars()), consent


def history_filter(patient_id: uuid.UUID, facility_id: uuid.UUID, consent: Consent | None):
    """SQL filter for history entries this facility may read."""
    base = [PatientHistoryEntry.patient_id == patient_id, PatientHistoryEntry.active.is_(True)]
    if consent:
        return and_(*base)
    return and_(*base, or_(PatientHistoryEntry.facility_id == facility_id, PatientHistoryEntry.facility_id.is_(None),
                           PatientHistoryEntry.kind == "allergy"))


async def hidden_history_count(db: AsyncSession, patient_id: uuid.UUID, facility_id: uuid.UUID) -> int:
    rows = (await db.execute(select(PatientHistoryEntry.id).where(
        PatientHistoryEntry.patient_id == patient_id, PatientHistoryEntry.active.is_(True),
        PatientHistoryEntry.facility_id.is_not(None), PatientHistoryEntry.facility_id != facility_id,
        PatientHistoryEntry.kind != "allergy"))).all()
    return len(rows)


def _short(name: str | None) -> str:
    return (name or "Unknown").replace(" (Demo)", "")


async def visits(db: AsyncSession, encounter_ids: list, *, include_notes: bool = True) -> list[dict]:
    """Visit summaries (newest first) with vitals, verified results, signed notes and prescriptions."""
    if not encounter_ids:
        return []
    encs = (await db.execute(select(Encounter, Facility.name).join(Facility, Facility.id == Encounter.facility_id)
                             .where(Encounter.id.in_(encounter_ids)).order_by(Encounter.created_at.desc()))).all()
    vit = (await db.execute(select(Vital).where(Vital.encounter_id.in_(encounter_ids)))).scalars().all()
    superseded = {v.corrected_from for v in vit if v.corrected_from}
    res = (await db.execute(
        select(InvestigationOrder, LabResult).join(LabResult, LabResult.order_id == InvestigationOrder.id)
        .where(InvestigationOrder.encounter_id.in_(encounter_ids), InvestigationOrder.status == "verified"))).all()
    notes = (await db.execute(select(ClinicalNote).where(ClinicalNote.encounter_id.in_(encounter_ids),
                                                         ClinicalNote.status == "signed"))).scalars().all() if include_notes else []
    rx = (await db.execute(select(Prescription).where(Prescription.encounter_id.in_(encounter_ids),
                                                      Prescription.status == "active"))).scalars().all()
    out = []
    for e, fac in encs:
        out.append({
            "encounter_id": str(e.id), "facility": _short(fac), "facility_id": str(e.facility_id),
            "date": e.created_at.isoformat(), "state": e.state, "complaint": e.chief_complaint,
            "disposition": e.disposition,
            "vitals": [{"kind": v.kind, "value": v.value, "unit": v.unit, "at": v.measured_at.isoformat()}
                       for v in vit if v.encounter_id == e.id and v.id not in superseded],
            "results": [{"test": o.test_name, "text": r.result_text, "abnormal": r.abnormal,
                         "at": (r.verified_at or r.entered_at).isoformat()} for o, r in res if o.encounter_id == e.id],
            "notes": [{"body": n.body, "signed_at": n.signed_at.isoformat() if n.signed_at else None}
                      for n in notes if n.encounter_id == e.id],
            "prescriptions": [{"drug": p.drug, "dose": p.dose} for p in rx if p.encounter_id == e.id],
        })
    return out


async def history_rows(db: AsyncSession, where) -> list[dict]:
    rows = (await db.execute(select(PatientHistoryEntry, Facility.name)
                             .outerjoin(Facility, Facility.id == PatientHistoryEntry.facility_id)
                             .where(where).order_by(PatientHistoryEntry.kind, PatientHistoryEntry.recorded_at))).all()
    return [{"kind": h.kind, "text": h.text, "detail": h.detail, "onset_age": h.onset_age,
             "source": _short(fac) if fac else "Patient-reported", "recorded_at": h.recorded_at.isoformat()}
            for h, fac in rows]


async def patient_timeline(db: AsyncSession, patient_id: uuid.UUID) -> dict:
    """Everything, for the patient's own phone. No disease names from triage; signed notes are theirs to read."""
    enc_ids = list((await db.execute(select(Encounter.id).where(Encounter.patient_id == patient_id))).scalars())
    reports = (await db.execute(select(TriageReport).where(TriageReport.patient_id == patient_id)
                                .order_by(TriageReport.created_at.desc()).limit(20))).scalars().all()
    refs = (await db.execute(select(Referral, Facility.name).join(Facility, Facility.id == Referral.facility_id)
                             .where(Referral.patient_id == patient_id).order_by(Referral.created_at.desc()))).all()
    chemist_vitals = (await db.execute(select(Vital).where(Vital.patient_id == patient_id, Vital.source == "worker")
                                       .order_by(Vital.measured_at.desc()))).scalars().all()
    return {
        "history": await history_rows(db, and_(PatientHistoryEntry.patient_id == patient_id,
                                               PatientHistoryEntry.active.is_(True))),
        "visits": await visits(db, enc_ids),
        "triage": [{"date": r.created_at.isoformat(), "action_level": r.action_level, "red_flag": r.red_flag}
                   for r in reports],
        "referrals": [{"id": str(r.id), "facility": _short(f), "status": r.status, "date": r.created_at.isoformat()}
                      for r, f in refs if r.status != "declined"],
        "chemist_vitals": [{"kind": v.kind, "value": v.value, "unit": v.unit, "at": v.measured_at.isoformat()}
                           for v in chemist_vitals],
    }


def is_live(c: Consent, now: datetime | None = None) -> bool:
    now = now or utcnow()
    return c.activated_at is not None and c.revoked_at is None and c.expires_at > now
