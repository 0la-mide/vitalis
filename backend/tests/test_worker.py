from datetime import timedelta

from sqlalchemy import select

from app.core.db import sessionmaker, utcnow
from app.models import Referral, User
from app.services.notify import ConsoleSms
from app.services.referrals import run_overdue_check

DISEASE_WORDS = ["haemorrhage", "likelihood", "malaria", "pneumonia", "condition_code"]


async def _walk_in(c, taps=None, phone=None):
    body = {"taps": taps or []}
    if phone:
        body["family_phone"] = phone
    r = await c.post("/api/v1/worker/triage", json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def test_walk_in_triage_vitals_and_refer(staff_client):
    chemist = await staff_client("chemist1@vitalis.demo")
    start = await _walk_in(chemist, [{"kind": "emergency", "code": "pregnancy"}], phone="+2348000000777")
    assert start["vitalis_id"].startswith("VT-") and len(start["recovery_code"]) == 14
    assert "device_key" not in start
    rid = start["triage"]["report_id"]
    # Defaults to the shop's location, not "approximate".
    assert start["triage"]["hospitals"]["approximate_location"] is False

    r = await chemist.post(f"/api/v1/worker/triage/{rid}/taps", json={"taps": [
        {"kind": "region", "region": "lower_abdomen"}, {"kind": "symptom", "code": "ABDOMINAL_PAIN"},
        {"kind": "severity", "value": 3}]})
    d = r.json()["data"]
    assert not d["red_flag"]["fired"] and d["care_type"] == "obstetrics"
    for w in DISEASE_WORDS:
        assert w not in r.text.lower()

    # Vitals: low blood pressure fires the red-flag rule straight away.
    r = await chemist.post(f"/api/v1/worker/patients/{start['patient_id']}/vitals", json={
        "report_id": rid, "readings": [{"kind": "systolic_bp", "value": 84}, {"kind": "pulse", "value": 118},
                                        {"kind": "spo2", "value": 97}]})
    d = r.json()["data"]
    assert d["red_flag"]["fired"] and d["action_level"] == "go_now" and d["heads_up_sent"]

    ref = (await chemist.post(f"/api/v1/worker/triage/{rid}/referral", json={})).json()["data"]
    assert ref["vitalis_id"] == start["vitalis_id"] and ref["status"] == "pending"

    # Hospital sees the chemist's vitals and name; accepts; worker list reflects it.
    doctor = await staff_client(f"doctor.{_slug(ref['facility_name'])}@vitalis.demo")
    item = (await doctor.get(f"/api/v1/hospital/referrals/{ref['id']}")).json()["data"]
    assert item["referred_by"].startswith("Mama Tola")
    assert {v["kind"] for v in item["vitals"]} >= {"systolic_bp", "pulse", "spo2"}
    assert all(v["source"] == "worker" for v in item["vitals"])
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    mine = (await chemist.get("/api/v1/worker/referrals")).json()["data"]
    assert mine[0]["id"] == ref["id"] and mine[0]["status"] == "accepted"


async def test_vitals_validation(staff_client):
    chemist = await staff_client("chemist1@vitalis.demo")
    start = await _walk_in(chemist)
    base = f"/api/v1/worker/patients/{start['patient_id']}/vitals"
    rid = start["triage"]["report_id"]
    r = await chemist.post(base, json={"report_id": rid, "readings": [{"kind": "spo2", "value": 140}]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "vital_out_of_range"
    r = await chemist.post(base, json={"report_id": rid, "readings": [{"kind": "glucose", "value": 5}]})
    assert r.status_code == 422
    future = (utcnow() + timedelta(hours=1)).isoformat()
    r = await chemist.post(base, json={"report_id": rid, "readings": [{"kind": "pulse", "value": 80,
                                                                       "measured_at": future}]})
    assert r.status_code == 422


async def test_worker_scoping(staff_client):
    tola = await staff_client("chemist1@vitalis.demo")
    okafor = await staff_client("chemist2@vitalis.demo")
    start = await _walk_in(tola, [{"kind": "emergency", "code": "cant_breathe"}])
    rid = start["triage"]["report_id"]
    ref = (await tola.post(f"/api/v1/worker/triage/{rid}/referral", json={})).json()["data"]

    assert (await okafor.get(f"/api/v1/worker/triage/{rid}")).status_code == 404
    assert (await okafor.post(f"/api/v1/worker/triage/{rid}/taps",
                              json={"taps": [{"kind": "severity", "value": 2}]})).status_code == 404
    assert (await okafor.post(f"/api/v1/worker/patients/{start['patient_id']}/vitals",
                              json={"report_id": rid, "readings": [{"kind": "pulse", "value": 80}]})).status_code == 404
    assert (await okafor.get(f"/api/v1/worker/referrals/{ref['id']}")).status_code == 404
    assert ref["id"] not in str((await okafor.get("/api/v1/worker/referrals")).json())


async def test_only_approved_workers(staff_client, client):
    pending = await staff_client("chemist3@vitalis.demo")
    assert (await pending.post("/api/v1/worker/triage", json={"taps": []})).status_code == 403
    nurse = await staff_client("nurse.central@vitalis.demo")
    assert (await nurse.post("/api/v1/worker/triage", json={"taps": []})).status_code == 403
    assert (await client.post("/api/v1/worker/triage", json={"taps": []})).status_code == 401


async def test_decline_visible_to_worker_with_reason(staff_client):
    chemist = await staff_client("chemist1@vitalis.demo")
    start = await _walk_in(chemist, [{"kind": "emergency", "code": "pregnancy"},
                                     {"kind": "region", "region": "pelvis"},
                                     {"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY"}])
    rid = start["triage"]["report_id"]
    ref = (await chemist.post(f"/api/v1/worker/triage/{rid}/referral", json={})).json()["data"]
    doctor = await staff_client(f"doctor.{_slug(ref['facility_name'])}@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "decline", "reason": "No bed"})
    got = (await chemist.get(f"/api/v1/worker/referrals/{ref['id']}")).json()["data"]
    assert got["status"] == "declined" and got["decision_reason"] == "No bed" and got["next_referral_id"]


async def test_overdue_notifies_worker(staff_client):
    chemist = await staff_client("chemist1@vitalis.demo")
    start = await _walk_in(chemist, [{"kind": "emergency", "code": "cant_breathe"}])
    ref = (await chemist.post(f"/api/v1/worker/triage/{start['triage']['report_id']}/referral",
                              json={})).json()["data"]
    doctor = await staff_client(f"doctor.{_slug(ref['facility_name'])}@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    ConsoleSms.sent.clear()
    async with sessionmaker()() as db:
        row = (await db.execute(select(Referral).where(Referral.id == ref["id"]))).scalar_one()
        row.accepted_at = utcnow() - timedelta(hours=2)
        worker = (await db.execute(select(User).where(User.email == "chemist1@vitalis.demo"))).scalar_one()
        await db.commit()
        await run_overdue_check(db)
    assert any(phone == worker.phone for phone, _ in ConsoleSms.sent)
    assert (await chemist.get(f"/api/v1/worker/referrals/{ref['id']}")).json()["data"]["status"] == "overdue"


def _slug(name: str) -> str:
    from app.seed import FACILITIES

    return next(f.slug for f in FACILITIES if f.name == name)


async def test_vitals_keep_model_care_type(staff_client):
    """Saving vitals re-runs rules without the model; the care type from the last prediction must stick."""
    chemist = await staff_client("chemist1@vitalis.demo")
    start = await _walk_in(chemist, [{"kind": "context", "age_group": "adult", "sex": "male"}])
    rid = start["triage"]["report_id"]
    r = await chemist.post(f"/api/v1/worker/triage/{rid}/taps", json={"taps": [
        {"kind": "region", "region": "whole_body"}, {"kind": "symptom", "code": "FEVER"},
        {"kind": "severity", "value": 3}, {"kind": "onset", "value": "days"}]})
    assert r.json()["data"]["care_type"] == "infectious_disease"
    r = await chemist.post(f"/api/v1/worker/patients/{start['patient_id']}/vitals", json={
        "report_id": rid, "readings": [{"kind": "temp_c", "value": 38.6}, {"kind": "pulse", "value": 104}]})
    d = r.json()["data"]
    assert not d["red_flag"]["fired"]
    assert d["care_type"] == "infectious_disease"
    assert (await chemist.get(f"/api/v1/worker/triage/{rid}")).json()["data"]["care_type"] == "infectious_disease"
