from datetime import timedelta

from sqlalchemy import select

from app.core.db import sessionmaker, utcnow
from app.models import Referral
from app.services.notify import ConsoleSms
from app.services.referrals import run_overdue_check
from tests.conftest import DEMO_LOCATION, new_patient


async def _demo_red_flag(client) -> str:
    await new_patient(client)
    r = await client.post("/api/v1/triage", json={"taps": [
        DEMO_LOCATION, {"kind": "emergency", "code": "pregnancy"}, {"kind": "region", "region": "pelvis"},
        {"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY", "region": "pelvis"}]})
    return r.json()["data"]["report_id"]


async def test_decline_offers_next_then_accept_and_arrive(client, staff_client):
    rid = await _demo_red_flag(client)
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    assert ref["facility"]["name"] == "Abeokuta Central Hospital (Demo)"
    assert ref["status"] == "pending"

    central = await staff_client("doctor.central@vitalis.demo")
    incoming = (await central.get("/api/v1/hospital/incoming")).json()["data"]
    assert any(i["id"] == ref["id"] and i["red_flag"] for i in incoming)

    # Decline requires a reason
    r = await central.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "decline"})
    assert r.status_code == 422
    r = await central.patch(f"/api/v1/hospital/referrals/{ref['id']}",
                            json={"action": "decline", "reason": "Theatre busy"})
    nxt_id = r.json()["data"]["next_referral_id"]
    assert nxt_id

    old = (await client.get(f"/api/v1/referrals/{ref['id']}")).json()["data"]
    assert old["status"] == "declined" and old["next_referral_id"] == nxt_id
    assert "Theatre" not in str(old)  # internal reason not shown to family
    nxt = (await client.get(f"/api/v1/referrals/{nxt_id}")).json()["data"]
    assert nxt["facility"]["name"] == "Sapon Mother & Child Hospital (Demo)"

    # Central cannot touch Sapon's referral (facility scoping / IDOR)
    assert (await central.get(f"/api/v1/hospital/referrals/{nxt_id}")).status_code == 404
    assert (await central.patch(f"/api/v1/hospital/referrals/{nxt_id}", json={"action": "accept"})).status_code == 404

    sapon = await staff_client("doctor.sapon@vitalis.demo")
    r = await sapon.patch(f"/api/v1/hospital/referrals/{nxt_id}", json={"action": "accept"})
    assert r.json()["data"]["status"] == "accepted"
    accepted = (await client.get(f"/api/v1/referrals/{nxt_id}")).json()["data"]
    assert accepted["status"] == "accepted" and accepted["eta_minutes"] > 0
    assert "openstreetmap.org" in accepted["directions_url"]
    assert accepted["what_to_bring"]

    # Doctor cannot confirm arrival; receptionist can.
    assert (await sapon.post(f"/api/v1/hospital/referrals/{nxt_id}/arrived")).status_code == 403
    desk = await staff_client("receptionist.sapon@vitalis.demo")
    assert (await desk.post(f"/api/v1/hospital/referrals/{nxt_id}/arrived")).json()["data"]["status"] == "arrived"


async def test_invalid_transition(client, staff_client):
    rid = await _demo_red_flag(client)
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    desk = await staff_client("receptionist.central@vitalis.demo")
    r = await desk.post(f"/api/v1/hospital/referrals/{ref['id']}/arrived")
    assert r.status_code == 409  # pending -> arrived is not allowed


async def test_heads_up_ready(client, staff_client):
    await _demo_red_flag(client)
    central = await staff_client("nurse.central@vitalis.demo")
    alerts = [i for i in (await central.get("/api/v1/hospital/incoming")).json()["data"] if i["kind"] == "alert"]
    assert alerts
    r = await central.post(f"/api/v1/hospital/alerts/{alerts[0]['id']}/ready")
    assert r.json()["data"]["status"] == "ready"
    other = await staff_client("nurse.kemta@vitalis.demo")
    # Another facility's nurse cannot see or act on Central's alert.
    assert (await other.post(f"/api/v1/hospital/alerts/{alerts[0]['id']}/ready")).status_code == 404


async def test_overdue_job(client, staff_client):
    rid = await _demo_red_flag(client)
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    central = await staff_client("doctor.central@vitalis.demo")
    await central.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    async with sessionmaker()() as db:
        assert await run_overdue_check(db) == 0
        r = (await db.execute(select(Referral).where(Referral.id == ref["id"]))).scalar_one()
        r.accepted_at = utcnow() - timedelta(hours=2)
        await db.commit()
        assert await run_overdue_check(db) == 1
    got = (await client.get(f"/api/v1/referrals/{ref['id']}")).json()["data"]
    assert got["status"] == "overdue"


async def test_overdue_sms_when_phone_given(client, staff_client):
    r = await client.post("/api/v1/patients/start", json={"phone": "+2348000000099"})
    client.headers["x-patient-key"] = r.json()["data"]["device_key"]
    rid = (await client.post("/api/v1/triage", json={"taps": [
        DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]["report_id"]
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    fac = await staff_client(f"doctor.{_slug(ref['facility']['name'])}@vitalis.demo")
    await fac.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    ConsoleSms.sent.clear()
    async with sessionmaker()() as db:
        row = (await db.execute(select(Referral).where(Referral.id == ref["id"]))).scalar_one()
        row.accepted_at = utcnow() - timedelta(hours=2)
        await db.commit()
        await run_overdue_check(db)
    assert ConsoleSms.sent and ConsoleSms.sent[0][0] == "+2348000000099"


def _slug(name: str) -> str:
    from app.seed import FACILITIES

    return next(f.slug for f in FACILITIES if f.name == name)


async def test_family_texted_when_hospital_accepts(client, staff_client):
    r = await client.post("/api/v1/patients/start", json={"phone": "0800 000 0077"})
    client.headers["x-patient-key"] = r.json()["data"]["device_key"]
    rid = (await client.post("/api/v1/triage", json={"taps": [
        DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]["report_id"]
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    ConsoleSms.sent.clear()
    fac = await staff_client(f"doctor.{_slug(ref['facility']['name'])}@vitalis.demo")
    await fac.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    assert len(ConsoleSms.sent) == 1
    phone, msg = ConsoleSms.sent[0]
    assert phone == "0800 000 0077" and ref["facility"]["name"] in msg and "ready" in msg
    assert "breath" not in msg.lower()  # no clinical details in an SMS
