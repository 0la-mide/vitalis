"""Name and NHIA number on a VITALIS ID: the patient edits them in the app; reception sees and corrects them."""

from sqlalchemy import select

from app.core.db import sessionmaker
from app.models import AuditEvent
from tests.conftest import DEMO_LOCATION, new_patient


async def test_patient_sets_own_name_and_nhia(client):
    me = await new_patient(client)
    r = await client.patch("/api/v1/me/profile", json={"full_name": "  Ada   Okafor ", "nhia_number": "nhia/og/001234"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d == {"vitalis_id": me["vitalis_id"], "full_name": "Ada Okafor", "nhia_number": "NHIA/OG/001234"}
    assert (await client.patch("/api/v1/me/profile", json={"nhia_number": "<script>"})).status_code == 422
    # Leaving a field out keeps it; "" clears it.
    d = (await client.patch("/api/v1/me/profile", json={"nhia_number": ""})).json()["data"]
    assert d["full_name"] == "Ada Okafor" and d["nhia_number"] is None
    assert (await client.get("/api/v1/me/profile")).json()["data"]["full_name"] == "Ada Okafor"


async def test_reception_sees_and_corrects_identity(client, staff_client):
    await new_patient(client)
    await client.patch("/api/v1/me/profile", json={"full_name": "Ada Okafor"})
    rid = (await client.post("/api/v1/triage", json={"taps": [
        DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]["report_id"]
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    slug = ref["facility"]["name"].split()[0].lower()
    desk = await staff_client(f"receptionist.{slug}@vitalis.demo")
    incoming = (await desk.get("/api/v1/hospital/incoming")).json()["data"]
    assert any(i["patient"]["name"] == "Ada Okafor" for i in incoming)

    doctor = await staff_client(f"doctor.{slug}@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    eid = (await desk.post(f"/api/v1/hospital/referrals/{ref['id']}/arrived")).json()["data"]["encounter_id"]
    r = await desk.patch(f"/api/v1/hospital/encounters/{eid}/patient",
                         json={"full_name": "A", "nhia_number": "NHIA/OG/9"})
    assert r.status_code == 422  # name too short
    r = await desk.patch(f"/api/v1/hospital/encounters/{eid}/patient",
                         json={"full_name": "Adaeze Okafor", "nhia_number": "NHIA/OG/0099"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["patient"]["name"] == "Adaeze Okafor"
    assert r.json()["data"]["patient"]["nhia_number"] == "NHIA/OG/0099"
    # The patient sees the correction on their phone.
    assert (await client.get("/api/v1/me/profile")).json()["data"]["full_name"] == "Adaeze Okafor"
    # Doctors don't edit identity; other hospitals can't touch it.
    assert (await doctor.patch(f"/api/v1/hospital/encounters/{eid}/patient", json={"full_name": "X Y"})).status_code == 403
    other = await staff_client("receptionist.kemta@vitalis.demo")
    assert (await other.patch(f"/api/v1/hospital/encounters/{eid}/patient", json={"full_name": "X Y"})).status_code == 404
    async with sessionmaker()() as db:
        assert (await db.execute(select(AuditEvent).where(AuditEvent.action == "patient.identity.update"))).first()


async def test_walk_ins_can_carry_a_name(staff_client):
    chemist = await staff_client("chemist1@vitalis.demo")
    r = await chemist.post("/api/v1/worker/triage", json={"taps": [DEMO_LOCATION], "full_name": "Musa Bello"})
    assert r.status_code == 200, r.text
    desk = await staff_client("receptionist.central@vitalis.demo")
    r = await desk.post("/api/v1/hospital/encounters", json={
        "full_name": "Grace Eze", "age_group": "adult", "chief_complaint": "Fever for two days"})
    assert r.status_code == 200, r.text
    enc = (await desk.get(f"/api/v1/hospital/encounters/{r.json()['data']['encounter_id']}")).json()["data"]
    assert enc["patient"]["name"] == "Grace Eze"
