"""Patients add their own allergies, conditions, medicines and family history; hospitals see them as patient-reported."""

from tests.conftest import DEMO_LOCATION, new_patient


async def test_patient_adds_and_removes_own_entries(client):
    await new_patient(client)
    r = await client.post("/api/v1/me/history", json={"kind": "allergy", "text": "Penicillin", "detail": "Rash"})
    assert r.status_code == 200, r.text
    rows = r.json()["data"]["history"]
    mine = next(h for h in rows if h["text"] == "Penicillin")
    assert mine["patient_reported"] and mine["source"] == "Patient-reported"
    assert (await client.post("/api/v1/me/history", json={"kind": "surgery", "text": "x y"})).status_code == 422
    r = await client.delete(f"/api/v1/me/history/{mine['id']}")
    assert all(h["text"] != "Penicillin" for h in r.json()["data"]["history"])


async def test_patient_cannot_remove_what_a_hospital_recorded(client):
    from sqlalchemy import select

    from app.core.db import sessionmaker
    from app.core.security import sha256_hex
    from app.models import Patient, PatientHistoryEntry
    async with sessionmaker()() as db:
        p = (await db.execute(select(Patient).where(Patient.display_name == "Mrs. Folake Adewale (demo)"))).scalar_one()
        p.device_key_hash = sha256_hex("folake-key-for-self-report-test")
        await db.commit()
        hospital_entry = (await db.execute(select(PatientHistoryEntry).where(
            PatientHistoryEntry.patient_id == p.id, PatientHistoryEntry.facility_id.is_not(None)))).scalars().first()
    client.headers["x-patient-key"] = "folake-key-for-self-report-test"
    assert (await client.delete(f"/api/v1/me/history/{hospital_entry.id}")).status_code == 404


async def test_patient_reported_allergy_reaches_the_doctor_and_safety_check(client, staff_client):
    await new_patient(client)
    await client.post("/api/v1/me/history", json={"kind": "allergy", "text": "Sulfonamides (Septrin)", "detail": "Swelling"})
    await client.patch("/api/v1/me/profile", json={"phone": "0803 000 0000"})
    assert (await client.get("/api/v1/me/profile")).json()["data"]["phone"] == "0803 000 0000"
    assert (await client.patch("/api/v1/me/profile", json={"phone": "call me"})).status_code == 422
    rid = (await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]["report_id"]
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    slug = ref["facility"]["name"].split()[0].lower()
    doctor = await staff_client(f"doctor.{slug}@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    desk = await staff_client(f"receptionist.{slug}@vitalis.demo")
    eid = (await desk.post(f"/api/v1/hospital/referrals/{ref['id']}/arrived")).json()["data"]["encounter_id"]
    rec = (await doctor.get(f"/api/v1/hospital/encounters/{eid}/record")).json()["data"]
    allergy = next(h for h in rec["history"] if h["kind"] == "allergy")
    assert allergy["source"] == "Patient-reported"
    chk = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/prescriptions/check", json={"drug": "Hydrochlorothiazide"})).json()["data"]
    assert chk["verdict"] in ("avoid", "caution")
