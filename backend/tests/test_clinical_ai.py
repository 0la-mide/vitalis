"""Doctor AI (ported from the team's NCS repo), the team's ML models, medication safety and safe prescribing."""

import json

import pytest

from app.engines.clinical.medication_safety import HistoryItem, check
from app.engines.llm import providers
from app.engines.ncs_models import adapter

DOSE_WORDS = [" mg", " mcg", " ml ", " tablets"]


async def _folake(doctor) -> str:
    board = (await doctor.get("/api/v1/hospital/encounters")).json()["data"]
    return next(e["id"] for e in board if e["state"] == "awaiting_doctor" and "thirst" in (e["headline"] or ""))


async def test_ai_flags_bp_diabetes_and_cross_hospital_allergy(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    eid = await _folake(doctor)
    r = await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    out = d["output"]
    assert d["action"] == "pending" and d["narrative_provider"] == "canned"

    titles = [f["title"] for f in out["red_flags"]]
    assert "Markedly raised BP with possible target-organ symptoms" in titles
    conds = {c["key"]: c for c in out["conditions"]}
    assert conds["hypertension"]["condition"].startswith("Uncontrolled stage 2 hypertension")
    assert "probable new diagnosis" in conds["diabetes"]["condition"]
    assert any("174" in e["text"] for e in conds["hypertension"]["evidence"])
    assert any("Raised systolic BP on 3 earlier visit" in e["text"] for e in conds["hypertension"]["evidence"])

    hctz = next(m for m in out["medication_options"] if m["drug"].startswith("Hydrochlorothiazide"))
    assert hctz["safety"] == "avoid"
    assert any("Sulfonamides" in a and "Ogun Teaching Hospital" in a for a in hctz["alerts"])

    # The team's models ran (bands, never percentages shown as the result)
    keys = {m["key"]: m for m in out["ml_models"]}
    assert set(keys) == {"diabetes", "heart"}
    assert keys["diabetes"]["band"] in ("Low", "Moderate", "High")
    assert any(i["source"] == "assumed" for i in keys["heart"]["inputs"])

    # The AI never suggests a dose: its options are drug names and reasons only. (Current medicines quoted from the
    # record may carry their recorded dose; that is a fact, not a suggestion.)
    blob = json.dumps([{k: m[k] for k in ("drug", "rationale")} for m in out["medication_options"]])
    assert not any(w in blob for w in DOSE_WORDS)
    assert "trend" in " ".join(out["analysis_trace"]).lower()


async def test_ai_runs_with_models_and_llm_disabled(staff_client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "enable_ncs_models", False)
    doctor = await staff_client("doctor.central@vitalis.demo")
    eid = await _folake(doctor)
    out = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).json()["data"]["output"]
    assert out["ml_models"] == []
    assert any("unavailable" in t for t in out["analysis_trace"])
    assert out["conditions"][0]["key"] in ("hypertension", "diabetes")


async def test_only_doctors_and_only_own_facility(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    eid = await _folake(doctor)
    nurse = await staff_client("nurse.central@vitalis.demo")
    assert (await nurse.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).status_code == 403
    other = await staff_client("doctor.sapon@vitalis.demo")
    assert (await other.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).status_code == 404
    assert (await other.get(f"/api/v1/hospital/encounters/{eid}/record")).status_code == 404


async def test_accept_puts_draft_in_note_and_reject_needs_reason(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    eid = await _folake(doctor)
    d1 = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).json()["data"]
    assert (await doctor.patch(f"/api/v1/hospital/ai-drafts/{d1['id']}", json={"action": "rejected"})).status_code == 422
    r = await doctor.patch(f"/api/v1/hospital/ai-drafts/{d1['id']}", json={"action": "rejected",
                                                                            "rationale": "Need examination first"})
    assert r.json()["data"]["action"] == "rejected"
    d2 = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).json()["data"]
    await doctor.patch(f"/api/v1/hospital/ai-drafts/{d2['id']}", json={"action": "accepted"})
    e = (await doctor.get(f"/api/v1/hospital/encounters/{eid}")).json()["data"]
    draft = next(n for n in e["notes"] if n["status"] == "draft")
    assert "VITALIS AI draft" in draft["body"] and "Avoid (record conflict): Hydrochlorothiazide" in draft["body"]
    assert (await doctor.patch(f"/api/v1/hospital/ai-drafts/{d2['id']}", json={"action": "accepted"})).status_code == 409


async def test_prescribing_is_safety_checked(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    eid = await _folake(doctor)
    base = f"/api/v1/hospital/encounters/{eid}/prescriptions"
    chk = (await doctor.post(f"{base}/check", json={"drug": "Hydrochlorothiazide"})).json()["data"]
    assert chk["verdict"] == "avoid"
    r = await doctor.post(base, json={"drug": "Hydrochlorothiazide", "dose": "12.5 mg once daily"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "safety_conflict"
    r = await doctor.post(base, json={"drug": "Lisinopril", "dose": "10 mg once daily"})
    assert r.status_code == 200
    rec = r.json()["data"]
    assert rec["prescriptions"][0]["drug"] == "Lisinopril"
    assert any(h["kind"] == "medication" and h["text"] == "Lisinopril" and h["here"] for h in rec["history"])
    # Override is allowed only with a reason, and it is audited.
    r = await doctor.post(base, json={"drug": "Hydrochlorothiazide", "dose": "12.5 mg once daily",
                                      "override_reason": "Allergy was a mild rash; specialist advice"})
    assert r.status_code == 200
    admin = await staff_client("admin@vitalis.demo")
    ev = (await admin.get("/api/v1/admin/audit?action=prescription.override")).json()["data"]
    assert ev and ev[0]["details"]["drug"] == "Hydrochlorothiazide"
    nurse = await staff_client("nurse.central@vitalis.demo")
    assert (await nurse.post(base, json={"drug": "Paracetamol", "dose": "1 g"})).status_code == 403


async def test_history_entries_and_structured_labs(staff_client):
    desk = await staff_client("receptionist.central@vitalis.demo")
    eid = (await desk.post("/api/v1/hospital/encounters", json={
        "age_group": "adult", "sex": "male", "emergency": True, "chief_complaint": "Fever and chills"})).json()["data"]["encounter_id"]
    nurse = await staff_client("nurse.central@vitalis.demo")
    r = await nurse.post(f"/api/v1/hospital/encounters/{eid}/history", json={"kind": "allergy", "text": "Penicillin"})
    assert r.json()["data"]["history"][0]["text"] == "Penicillin"
    doctor = await staff_client("doctor.central@vitalis.demo")
    e = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/orders", json={"items": [{"test_code": "MP_RDT"}]})).json()["data"]
    lab = await staff_client("lab.central@vitalis.demo")
    oid = e["orders"][0]["id"]
    row = (await lab.post(f"/api/v1/hospital/orders/{oid}/result",
                          json={"values": {"Malaria RDT": {"value": "Positive"}}})).json()["data"]
    assert row["abnormal"] is True and row["values"]["Malaria RDT"]["flag"] == "POS"
    await lab.post(f"/api/v1/hospital/orders/{oid}/verify")
    out = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).json()["data"]["output"]
    amox = [m for m in out["medication_options"] if m["drug"] == "Amoxicillin"]
    assert not amox or amox[0]["safety"] == "avoid"  # penicillin allergy blocks amoxicillin when suggested
    assert any(c["key"] == "malaria" for c in out["conditions"])


def test_medication_safety_rules():
    allergy = [HistoryItem("Penicillin", "Central · Jan")]
    assert check("Amoxicillin", allergy, [], []).verdict == "avoid"
    assert check("Lisinopril", [], [], [], pregnant=True).verdict == "avoid"
    assert check("Simvastatin", [], [HistoryItem("Amlodipine")], []).verdict == "caution"
    assert check("Ibuprofen", [], [], [HistoryItem("Peptic ulcer")]).verdict == "caution"
    assert check("Paracetamol", allergy, [], []).verdict == "ok"


def test_llm_output_with_a_dose_is_rejected():
    good = json.dumps({"summary": "Raised BP and probable diabetes; avoid thiazide due to sulfonamide allergy."})
    assert providers._validate("gemini", good).provider == "gemini"
    with pytest.raises(ValueError):
        providers._validate("gemini", json.dumps({"summary": "Start lisinopril 10 mg daily."}))


def test_model_files_are_integrity_checked(tmp_path, monkeypatch):
    from app.core.config import get_settings

    (tmp_path / "diabetes_prediction_pipeline.joblib").write_bytes(b"tampered")
    monkeypatch.setattr(get_settings(), "ncs_model_dir", str(tmp_path))
    adapter._cache.clear()
    with pytest.raises(adapter.ModelUnavailable, match="integrity"):
        adapter.predict_diabetes({})
    adapter._cache.clear()
