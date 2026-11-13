"""Receiving hospital: a referred patient goes from arrival to a completed encounter with no re-typing."""

import pytest

from tests.conftest import DEMO_LOCATION


async def _referred_to_sapon(staff_client, *, red_flag: bool):
    """A chemist refers a walk-in with vitals; Sapon accepts. Returns (chemist, ref)."""
    chemist = await staff_client("chemist1@vitalis.demo")
    taps = [DEMO_LOCATION, {"kind": "emergency", "code": "pregnancy"}, {"kind": "region", "region": "pelvis"}]
    taps.append({"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY" if red_flag else "VAGINAL_DISCHARGE"})
    start = (await chemist.post("/api/v1/worker/triage", json={"taps": taps})).json()["data"]
    rid = start["triage"]["report_id"]
    await chemist.post(f"/api/v1/worker/patients/{start['patient_id']}/vitals", json={
        "report_id": rid, "readings": [{"kind": "pulse", "value": 118}, {"kind": "systolic_bp", "value": 96}]})
    facs = (await chemist.post(f"/api/v1/worker/triage/{rid}/taps", json={"taps": [{"kind": "severity", "value": 2}]}
                               )).json()["data"]["hospitals"]["top"]
    sapon = next(f for f in facs if f["name"].startswith("Sapon"))
    ref = (await chemist.post(f"/api/v1/worker/triage/{rid}/referral",
                              json={"facility_id": sapon["facility_id"]})).json()["data"]
    doctor = await staff_client("doctor.sapon@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    return chemist, ref


async def test_referral_arrival_to_completed(staff_client):
    chemist, ref = await _referred_to_sapon(staff_client, red_flag=False)
    desk = await staff_client("receptionist.sapon@vitalis.demo")
    nurse = await staff_client("nurse.sapon@vitalis.demo")
    doctor = await staff_client("doctor.sapon@vitalis.demo")
    lab = await staff_client("lab.sapon@vitalis.demo")
    radiology = await staff_client("radiology.sapon@vitalis.demo")

    # Reception: arrival opens the encounter, pre-filled from the referral.
    arr = (await desk.post(f"/api/v1/hospital/referrals/{ref['id']}/arrived")).json()["data"]
    eid = arr["encounter_id"]
    assert eid
    e = (await nurse.get(f"/api/v1/hospital/encounters/{eid}")).json()["data"]
    assert e["state"] == "awaiting_nursing" and not e["emergency"]
    assert e["referral"]["referred_by"].startswith("Mama Tola")
    assert [s["code"] for s in e["referral"]["symptoms"]] == ["VAGINAL_DISCHARGE"]
    chemist_pulse = next(v for v in e["vitals"] if v["kind"] == "pulse")
    assert chemist_pulse["source"] == "worker" and chemist_pulse["value"] == 118

    # Nursing: new readings sit next to the chemist's; an urgent one is flagged.
    e = (await nurse.post(f"/api/v1/hospital/encounters/{eid}/vitals", json={"readings": [
        {"kind": "pulse", "value": 96}, {"kind": "spo2", "value": 89}]})).json()["data"]
    nurse_rows = [v for v in e["vitals"] if v["source"] == "nurse"]
    assert {v["kind"] for v in nurse_rows} == {"pulse", "spo2"}
    assert next(v for v in nurse_rows if v["kind"] == "spo2")["urgent"] is True
    assert next(v for v in nurse_rows if v["kind"] == "pulse")["urgent"] is False

    # Correction keeps the original.
    spo2 = next(v for v in nurse_rows if v["kind"] == "spo2")
    r = await nurse.post(f"/api/v1/hospital/encounters/{eid}/vitals", json={
        "readings": [{"kind": "spo2", "value": 95}], "corrected_from": spo2["id"], "correction_reason": "Probe slipped"})
    e = r.json()["data"]
    old = next(v for v in e["vitals"] if v["id"] == spo2["id"])
    assert old["superseded"] and old["value"] == 89
    assert any(v["corrected_from"] == spo2["id"] and v["value"] == 95 for v in e["vitals"])

    # Doctor cannot be skipped to; nurse hands off.
    assert (await doctor.post(f"/api/v1/hospital/encounters/{eid}/notes", json={"body": "x"})).status_code == 200
    e = (await nurse.post(f"/api/v1/hospital/encounters/{eid}/transition",
                          json={"to": "awaiting_doctor"})).json()["data"]
    assert e["state"] == "awaiting_doctor"

    # Doctor: orders tests -> awaiting_investigation.
    e = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/orders", json={"items": [
        {"test_code": "FBC"}, {"test_code": "USS_OBS", "priority": "urgent"}]})).json()["data"]
    assert e["state"] == "awaiting_investigation" and len(e["orders"]) == 2

    # Each department sees only its own orders: the blood test goes to the lab, the scan to radiology.
    lab_q = [q for q in (await lab.get("/api/v1/hospital/lab/queue")).json()["data"] if q["encounter_id"] == eid]
    rad_q = [q for q in (await radiology.get("/api/v1/hospital/lab/queue")).json()["data"] if q["encounter_id"] == eid]
    assert [q["order"]["test_code"] for q in lab_q] == ["FBC"]
    assert [q["order"]["test_code"] for q in rad_q] == ["USS_OBS"] and rad_q[0]["order"]["priority"] == "urgent"
    fbc, scan = lab_q[0]["order"]["id"], rad_q[0]["order"]["id"]
    assert (await lab.post(f"/api/v1/hospital/orders/{scan}/result", json={"result_text": "x"})).status_code == 404
    assert (await radiology.post(f"/api/v1/hospital/orders/{scan}/collect")).status_code == 409  # no sample for a scan

    # Lab: sample collected -> result -> separate verify.
    r = await lab.post(f"/api/v1/hospital/orders/{fbc}/collect")
    assert r.json()["data"]["status"] == "collected" and r.json()["data"]["collected_by"]
    assert (await lab.post(f"/api/v1/hospital/orders/{fbc}/verify")).status_code == 409  # result first
    for c, oid in ((lab, fbc), (radiology, scan)):
        r = await c.post(f"/api/v1/hospital/orders/{oid}/result", json={"result_text": "Within normal limits"})
        assert r.json()["data"]["status"] == "resulted"
    e = (await doctor.get(f"/api/v1/hospital/encounters/{eid}")).json()["data"]
    assert e["state"] == "awaiting_investigation"  # resulted but not verified yet
    await lab.post(f"/api/v1/hospital/orders/{fbc}/verify")
    await radiology.post(f"/api/v1/hospital/orders/{scan}/verify")
    e = (await doctor.get(f"/api/v1/hospital/encounters/{eid}")).json()["data"]
    assert e["state"] == "results_ready"
    assert all(o["status"] == "verified" and o["verified_by"] for o in e["orders"])

    # Disposition needs a signed note.
    r = await doctor.post(f"/api/v1/hospital/encounters/{eid}/transition",
                          json={"to": "awaiting_disposition", "disposition": "discharged"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "note_required"
    draft = next(n for n in e["notes"] if n["status"] == "draft")
    e = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/notes",
                           json={"body": "Mild discharge, results normal. Review in clinic.",
                                 "note_id": draft["id"]})).json()["data"]
    e = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/notes/{draft['id']}/sign")).json()["data"]
    assert e["notes"][0]["status"] == "signed"
    e = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/transition",
                           json={"to": "awaiting_disposition", "disposition": "discharged"})).json()["data"]
    assert e["state"] == "awaiting_disposition"
    e = (await desk.post(f"/api/v1/hospital/encounters/{eid}/transition", json={"to": "completed"})).json()["data"]
    assert e["state"] == "completed" and e["completed_at"]

    # Timeline has every handoff with staff names; referral is completed; chemist sees it.
    summaries = [t["summary"] for t in e["timeline"]]
    assert summaries[0] == "Arrived by referral"
    assert any("Waiting for nurse → Waiting for doctor" in s for s in summaries)
    assert any(s.startswith("Corrected spo2") for s in summaries)
    assert any("All results verified" in s for s in summaries)
    assert all(t["actor"] for t in e["timeline"])
    mine = (await chemist.get(f"/api/v1/worker/referrals/{ref['id']}")).json()["data"]
    assert mine["status"] == "completed"


async def test_red_flag_skips_to_doctor(staff_client):
    _, ref = await _referred_to_sapon(staff_client, red_flag=True)
    desk = await staff_client("receptionist.sapon@vitalis.demo")
    eid = (await desk.post(f"/api/v1/hospital/referrals/{ref['id']}/arrived")).json()["data"]["encounter_id"]
    e = (await desk.get(f"/api/v1/hospital/encounters/{eid}")).json()["data"]
    assert e["emergency"] and e["state"] == "awaiting_doctor"
    assert "Emergency: straight to doctor" in [t["summary"] for t in e["timeline"]]


async def test_walk_in_registration(staff_client):
    desk = await staff_client("receptionist.central@vitalis.demo")
    r = await desk.post("/api/v1/hospital/encounters", json={
        "age_group": "adult", "sex": "male", "chief_complaint": "Leg cut from motorbike fall"})
    d = r.json()["data"]
    assert d["vitalis_id"].startswith("VT-") and d["recovery_code"]
    board = (await desk.get("/api/v1/hospital/encounters")).json()["data"]
    assert any(x["id"] == d["encounter_id"] and x["state"] == "awaiting_nursing" for x in board)


@pytest.mark.parametrize("email,action,expect", [
    ("receptionist.central@vitalis.demo", "vitals", 403),
    ("lab.central@vitalis.demo", "vitals", 403),
    ("nurse.central@vitalis.demo", "notes", 403),
    ("nurse.central@vitalis.demo", "orders", 403),
    ("doctor.central@vitalis.demo", "result", 403),
])
async def test_roles(staff_client, email, action, expect):
    desk = await staff_client("receptionist.central@vitalis.demo")
    eid = (await desk.post("/api/v1/hospital/encounters", json={
        "age_group": "adult", "emergency": True, "chief_complaint": "Collapsed"})).json()["data"]["encounter_id"]
    c = await staff_client(email)
    base = f"/api/v1/hospital/encounters/{eid}"
    if action == "vitals":
        r = await c.post(f"{base}/vitals", json={"readings": [{"kind": "pulse", "value": 80}]})
    elif action == "notes":
        r = await c.post(f"{base}/notes", json={"body": "note"})
    elif action == "orders":
        r = await c.post(f"{base}/orders", json={"items": [{"test_code": "FBC"}]})
    else:
        doctor = await staff_client("doctor.central@vitalis.demo") if email != "doctor.central@vitalis.demo" else c
        e = (await doctor.post(f"{base}/orders", json={"items": [{"test_code": "FBC"}]})).json()["data"]
        r = await c.post(f"/api/v1/hospital/orders/{e['orders'][0]['id']}/result", json={"result_text": "x"})
    assert r.status_code == expect


async def test_encounter_scoping(staff_client):
    desk = await staff_client("receptionist.central@vitalis.demo")
    d = (await desk.post("/api/v1/hospital/encounters", json={
        "age_group": "adult", "chief_complaint": "Headache"})).json()["data"]
    other = await staff_client("nurse.sapon@vitalis.demo")
    eid = d["encounter_id"]
    assert (await other.get(f"/api/v1/hospital/encounters/{eid}")).status_code == 404
    assert (await other.post(f"/api/v1/hospital/encounters/{eid}/vitals",
                             json={"readings": [{"kind": "pulse", "value": 80}]})).status_code == 404
    assert eid not in str((await other.get("/api/v1/hospital/encounters")).json())
    chemist = await staff_client("chemist1@vitalis.demo")
    assert (await chemist.get(f"/api/v1/hospital/encounters/{eid}")).status_code == 403


async def test_signed_note_is_never_edited(staff_client):
    desk = await staff_client("receptionist.central@vitalis.demo")
    eid = (await desk.post("/api/v1/hospital/encounters", json={
        "age_group": "adult", "emergency": True, "chief_complaint": "Chest pain"})).json()["data"]["encounter_id"]
    doctor = await staff_client("doctor.central@vitalis.demo")
    base = f"/api/v1/hospital/encounters/{eid}"
    e = (await doctor.post(f"{base}/notes", json={"body": "First note"})).json()["data"]
    nid = e["notes"][0]["id"]
    await doctor.post(f"{base}/notes/{nid}/sign")
    e = (await doctor.post(f"{base}/notes", json={"body": "Amended", "note_id": nid})).json()["data"]
    signed = next(n for n in e["notes"] if n["id"] == nid)
    amend = next(n for n in e["notes"] if n["id"] != nid)
    assert signed["body"] == "First note" and signed["status"] == "signed"
    assert amend["version"] == 2 and amend["supersedes_id"] == nid and amend["status"] == "draft"
    # A signed note cannot be signed (or changed) again.
    assert (await doctor.post(f"{base}/notes/{nid}/sign")).status_code == 409


async def test_cancel_needs_reason_and_role(staff_client):
    desk = await staff_client("receptionist.central@vitalis.demo")
    eid = (await desk.post("/api/v1/hospital/encounters", json={
        "age_group": "adult", "chief_complaint": "Fever"})).json()["data"]["encounter_id"]
    url = f"/api/v1/hospital/encounters/{eid}/transition"
    nurse = await staff_client("nurse.central@vitalis.demo")
    assert (await nurse.post(url, json={"to": "cancelled", "reason": "x"})).status_code == 403
    assert (await desk.post(url, json={"to": "cancelled"})).status_code == 422
    e = (await desk.post(url, json={"to": "cancelled", "reason": "Left before being seen"})).json()["data"]
    assert e["state"] == "cancelled"
