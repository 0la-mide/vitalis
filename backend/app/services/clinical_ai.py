"""Builds the doctor-AI input from the database and stores each run as an AI draft."""

import asyncio
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.errors import AppError
from app.engines.clinical import assessment as ai
from app.engines.clinical.medication_safety import HistoryItem
from app.engines.llm import providers
from app.engines.triage.data import symptom_index
from app.models import (
    AIDraft,
    ClinicalNote,
    Encounter,
    Facility,
    InvestigationOrder,
    LabResult,
    Patient,
    PatientHistoryEntry,
    TriageReport,
    User,
    Vital,
)
from app.services import records


def _short(name: str | None) -> str:
    return (name or "Unknown facility").replace(" (Demo)", "")


async def history_items(db: AsyncSession, patient_id: uuid.UUID, facility_id: uuid.UUID) -> dict[str, list[HistoryItem]]:
    """What this facility may read of the patient's record, each item labelled with where and when it was recorded.

    Allergies are always included (safety); other hospitals' entries need the patient's consent.
    """
    consent = await records.active_consent(db, patient_id, facility_id)
    rows = (await db.execute(
        select(PatientHistoryEntry, Facility.name)
        .outerjoin(Facility, Facility.id == PatientHistoryEntry.facility_id)
        .where(records.history_filter(patient_id, facility_id, consent))
        .order_by(PatientHistoryEntry.recorded_at)
    )).all()
    out: dict[str, list[HistoryItem]] = {"allergy": [], "condition": [], "medication": [], "family": []}
    for h, fac in rows:
        src = f"{_short(fac)} · {h.recorded_at:%d %b %Y}" if fac else f"Patient-reported · {h.recorded_at:%d %b %Y}"
        if h.kind == "family":
            text = f"{h.detail}: {h.text}" if h.detail else h.text
            if h.onset_age:
                text += f" (onset {h.onset_age})"
        elif h.kind == "allergy" and h.detail:
            text = f"{h.text}"
        else:
            text = h.text + (f" {h.detail}" if h.kind == "medication" and h.detail else "")
        out.setdefault(h.kind, []).append(HistoryItem(text=text, source=src))
    return out


async def build_record(db: AsyncSession, enc: Encounter) -> ai.Record:
    patient = await db.get(Patient, enc.patient_id)
    facility = await db.get(Facility, enc.facility_id)
    assert patient and facility
    report = await db.get(TriageReport, enc.report_id) if enc.report_id else None

    # Visits this facility may read: its own, plus other hospitals' when the patient has shared their record.
    ids, _consent = await records.visible_encounter_ids(db, patient.id, enc.facility_id)
    visible = (await db.execute(select(Encounter).where(Encounter.id.in_(ids)).order_by(Encounter.created_at))).scalars().all()
    fac_names = {f.id: _short(f.name) for f in (await db.execute(select(Facility))).scalars()}

    conds = [Vital.encounter_id.in_(ids)]
    if enc.report_id:
        conds.append(Vital.report_id == enc.report_id)
    vitals = (await db.execute(select(Vital).where(Vital.patient_id == patient.id, or_(*conds)))).scalars().all()
    superseded = {v.corrected_from for v in vitals if v.corrected_from}
    worker = await db.get(User, report.worker_id) if report and report.worker_id else None
    readings = []
    for v in vitals:
        if v.id in superseded:
            continue
        today = v.encounter_id == enc.id or (enc.report_id is not None and v.report_id == enc.report_id)
        visit_fac = next((e.facility_id for e in visible if e.id == v.encounter_id), facility.id)
        where = f"Referring chemist ({worker.full_name})" if v.source == "worker" and worker else fac_names[visit_fac]
        readings.append(ai.Reading(kind=v.kind, value=v.value, at=v.measured_at, facility=where, today=today))

    labs: list[ai.LabValue] = []
    rows = (await db.execute(
        select(InvestigationOrder, LabResult).join(LabResult, LabResult.order_id == InvestigationOrder.id)
        .where(InvestigationOrder.encounter_id.in_(ids), InvestigationOrder.status == "verified")
    )).all()
    for order, res in rows:
        when = res.verified_at or res.entered_at
        today = order.encounter_id == enc.id
        for param, val in (res.values or {}).items():
            key = ai.lab_key(param)
            if not key:
                continue
            raw = val.get("value") if isinstance(val, dict) else val
            try:
                num = float(raw)
            except (TypeError, ValueError):
                num = None
            labs.append(ai.LabValue(key=key, value=raw, num=num, unit=val.get("unit") if isinstance(val, dict) else None,
                                    at=when, facility=fac_names[order.facility_id], test=order.test_name, today=today))
        if order.test_code in ("MP_RDT", "MP_FILM") and not res.values:
            labs.append(ai.LabValue(key="malaria", value=res.result_text, num=None, unit=None, at=when,
                                    facility=fac_names[order.facility_id], test=order.test_name, today=today))

    idx = symptom_index()
    parts = [enc.chief_complaint or ""]
    if report:
        parts += [idx.get(s["code"], {}).get("labels", {}).get("en", s["code"]) for s in (report.answers or {}).get("symptoms", [])]
    notes = (await db.execute(select(ClinicalNote).where(ClinicalNote.encounter_id.in_(ids)))).scalars().all()
    enc_fac = {e.id: e.facility_id for e in visible}
    note_blobs = [(f"{fac_names[enc_fac[n.encounter_id]]} · {n.created_at:%d %b %Y}", n.body.lower())
                  for n in notes if n.status == "signed"]
    complaint = ", ".join(p for p in parts if p).strip(", ")

    hist = await history_items(db, patient.id, enc.facility_id)
    ctx = (report.context if report else None) or {}
    age, age_src = ai.age_from(patient.date_of_birth, ctx.get("age_group") or patient.age_group)
    prior = [e for e in visible if e.id != enc.id]
    return ai.Record(
        sex=ctx.get("sex") or patient.sex or "unknown",
        pregnant=bool(ctx.get("pregnant") or patient.pregnant),
        age=age, age_source=age_src, here=fac_names[facility.id], complaint=complaint,
        readings=readings, labs=labs,
        allergies=hist["allergy"], conditions=hist["condition"], medications=hist["medication"], family=hist["family"],
        prior_visits=len(prior), prior_facilities=sorted({fac_names[e.facility_id] for e in prior}),
        notes=note_blobs,
    )


async def run_for_encounter(db: AsyncSession, enc: Encounter, doctor: User) -> AIDraft:
    if enc.state in ("completed", "cancelled"):
        raise AppError(409, "invalid_state", "Encounter is closed")
    record = await build_record(db, enc)
    # Model inference is CPU work: keep it off the event loop.
    output = await asyncio.to_thread(lambda: ai.Assessment(record).run())
    narrative = await providers.narrate(output)
    output["narrative"] = narrative.as_dict()
    draft = AIDraft(
        encounter_id=enc.id, requested_by=doctor.id, engine_version=output["engine_version"],
        model_versions=[m["model_version"] for m in output["ml_models"]], narrative_provider=narrative.provider,
        inputs={"complaint": record.complaint, "vitals": [r.kind for r in record.readings],
                "labs": [lv.key for lv in record.labs], "allergies": len(record.allergies),
                "medications": len(record.medications), "prior_visits": record.prior_visits},
        output=output,
    )
    db.add(draft)
    await db.flush()
    await audit(db, "ai.draft.create", actor_id=doctor.id, subject_type="encounter", subject_id=enc.id,
                facility_id=enc.facility_id, details={"draft": str(draft.id), "provider": narrative.provider,
                                                      "models": draft.model_versions})
    return draft


def draft_note_text(output: dict) -> str:
    """What 'Accept' puts into the doctor's draft note. The doctor edits and signs; nothing is recorded until then."""
    lines = ["Assessment (VITALIS AI draft, reviewed by clinician):", output["narrative"]["summary"], ""]
    if output["red_flags"]:
        lines.append("Red flags: " + "; ".join(f["title"] for f in output["red_flags"]))
    lines.append("Considerations: " + "; ".join(f"{c['condition']} ({c['likelihood_label'].lower()})"
                                                for c in output["conditions"][:3]))
    avoid = [m["drug"] for m in output["medication_options"] if m["safety"] == "avoid"]
    if avoid:
        lines.append("Avoid (record conflict): " + ", ".join(avoid))
    lines += ["", "Plan:", "- "]
    return "\n".join(lines)

