"""Shared patient record + consent: QR (10 min, single use), access requests, referral sharing, revoke, audit."""

from datetime import timedelta

import httpx
from httpx import ASGITransport
from sqlalchemy import select, text

from app.core.db import sessionmaker, utcnow
from app.core.security import sha256_hex
from app.main import app
from app.models import Facility, Patient, PatientHistoryEntry, QRGrant

FOLAKE_KEY = "folake-test-device-key-0123456789abcdef"


async def folake_phone() -> httpx.AsyncClient:
    """Give Folake a known device key (the seed only stores hashes) and return her 'phone'."""
    async with sessionmaker()() as db:
        p = (await db.execute(select(Patient).where(Patient.display_name == "Mrs. Folake Adewale (demo)"))).scalar_one()
        p.device_key_hash = sha256_hex(FOLAKE_KEY)
        await db.commit()
    c = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    c.headers["x-patient-key"] = FOLAKE_KEY
    return c


async def folake_encounter(doctor) -> dict:
    board = (await doctor.get("/api/v1/hospital/encounters")).json()["data"]
    return next(e for e in board if "thirst" in (e["headline"] or ""))


async def facility_id(name_start: str) -> str:
    async with sessionmaker()() as db:
        return str((await db.execute(select(Facility.id).where(Facility.name.startswith(name_start)))).scalar_one())


async def patient_id_of(eid: str, staff) -> str:
    async with sessionmaker()() as db:
        return str((await db.execute(text("select patient_id from encounters where id = :i"), {"i": eid})).scalar_one())


async def test_my_record_on_the_phone():
    phone = await folake_phone()
    rec = (await phone.get("/api/v1/me/records")).json()["data"]
    assert {v["facility"] for v in rec["visits"]} == {"Lafenwa General Hospital", "Ogun Teaching Hospital",
                                                      "Abeokuta Central Hospital"}
    assert any(h["kind"] == "allergy" and h["source"] == "Ogun Teaching Hospital" for h in rec["history"])
    await phone.aclose()
    anon = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    assert (await anon.get("/api/v1/me/records")).status_code == 401


async def test_qr_share_unlocks_other_hospitals_for_the_ai(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    enc = await folake_encounter(doctor)
    eid = enc["id"]
    pid = await patient_id_of(eid, doctor)

    before = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).json()["data"]["output"]
    assert before["data_coverage"]["prior_visits"] == 1  # only Central's own visit
    st = (await doctor.get(f"/api/v1/hospital/patients/{pid}/consent")).json()["data"]
    assert st["active"] is False and st["other_hospital_visits"] == 2
    assert (await doctor.get(f"/api/v1/hospital/patients/{pid}/network-record")).status_code == 403

    phone = await folake_phone()
    share = (await phone.post("/api/v1/me/consents", json={})).json()["data"]
    assert share["url"].endswith(share["url"].split("/scan/")[1]) and share["qr_png"].startswith("data:image/png;base64,")
    token = share["url"].split("/scan/")[1]
    async with sessionmaker()() as db:
        g = (await db.execute(select(QRGrant))).scalars().all()
        assert all(x.token_hash != token for x in g)  # only the hash is stored

    r = await doctor.post("/api/v1/qr/redeem", json={"token": token})
    assert r.status_code == 200 and r.json()["data"]["encounter_id"] == eid
    # Single use
    assert (await doctor.post("/api/v1/qr/redeem", json={"token": token})).json()["error"]["code"] == "qr_used"

    net = (await doctor.get(f"/api/v1/hospital/patients/{pid}/network-record")).json()["data"]
    assert {v["facility"] for v in net["visits"]} == {"Lafenwa General Hospital", "Ogun Teaching Hospital"}

    after = (await doctor.post(f"/api/v1/hospital/encounters/{eid}/ai-draft")).json()["data"]["output"]
    assert after["data_coverage"]["prior_visits"] == 3
    sbp = next(t for t in after["trends"] if t["metric"] == "systolic_bp")
    assert "148 → 152 → 156 → 174" in sbp["text"] and "3 facilities" in sbp["text"]

    # The patient sees who looked, and can revoke
    log = (await phone.get("/api/v1/me/access-log")).json()["data"]
    assert any(e["what"].startswith("opened your shared record") for e in log["events"])
    assert any(e["what"] == "viewed your records from other hospitals" and e["who"] for e in log["events"])
    live = next(c for c in log["consents"] if c["active"])
    assert (await phone.delete(f"/api/v1/me/consents/{live['id']}")).status_code == 200
    assert (await doctor.get(f"/api/v1/hospital/patients/{pid}/network-record")).status_code == 403
    await phone.aclose()


async def test_expired_revoked_and_wrong_hospital_qr_fail(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    phone = await folake_phone()

    t1 = (await phone.post("/api/v1/me/consents", json={})).json()["data"]["url"].split("/scan/")[1]
    async with sessionmaker()() as db:
        g = (await db.execute(select(QRGrant).where(QRGrant.token_hash == sha256_hex(t1)))).scalar_one()
        g.expires_at = utcnow() - timedelta(seconds=1)
        await db.commit()
    assert (await doctor.post("/api/v1/qr/redeem", json={"token": t1})).json()["error"]["code"] == "qr_expired"

    s2 = (await phone.post("/api/v1/me/consents", json={})).json()["data"]
    await phone.delete(f"/api/v1/me/consents/{s2['consent_id']}")
    t2 = s2["url"].split("/scan/")[1]
    assert (await doctor.post("/api/v1/qr/redeem", json={"token": t2})).json()["error"]["code"] == "qr_revoked"

    sapon = await facility_id("Sapon")
    t3 = (await phone.post("/api/v1/me/consents", json={"facility_id": sapon})).json()["data"]["url"].split("/scan/")[1]
    r = await doctor.post("/api/v1/qr/redeem", json={"token": t3})
    assert r.status_code == 403 and r.json()["error"]["code"] == "qr_other_facility"

    assert (await doctor.post("/api/v1/qr/redeem", json={"token": "x" * 43})).status_code == 404
    # Patients and frontline workers cannot redeem
    chemist = await staff_client("chemist1@vitalis.demo")
    assert (await chemist.post("/api/v1/qr/redeem", json={"token": t3})).status_code == 403
    await phone.aclose()


async def test_access_request_allow_and_deny(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    pid = await patient_id_of((await folake_encounter(doctor))["id"], doctor)
    # A hospital with no visit or referral for this patient cannot even ask.
    stranger = await staff_client("doctor.kemta@vitalis.demo")
    assert (await stranger.post(f"/api/v1/hospital/patients/{pid}/access-requests", json={})).status_code == 404

    r = await doctor.post(f"/api/v1/hospital/patients/{pid}/access-requests", json={"purpose": "Today's visit"})
    assert r.json()["data"]["pending_request"] is True
    phone = await folake_phone()
    reqs = (await phone.get("/api/v1/me/access-requests")).json()["data"]
    assert reqs[0]["facility_name"].startswith("Abeokuta Central") and reqs[0]["requested_by"]
    await phone.post(f"/api/v1/me/access-requests/{reqs[0]['id']}", json={"decision": "deny"})
    assert (await doctor.get(f"/api/v1/hospital/patients/{pid}/consent")).json()["data"]["active"] is False

    await doctor.post(f"/api/v1/hospital/patients/{pid}/access-requests", json={})
    req = (await phone.get("/api/v1/me/access-requests")).json()["data"][0]
    await phone.post(f"/api/v1/me/access-requests/{req['id']}", json={"decision": "allow"})
    st = (await doctor.get(f"/api/v1/hospital/patients/{pid}/consent")).json()["data"]
    assert st["active"] is True and st["consent"]["via"] == "access_request"
    assert (await phone.post(f"/api/v1/me/access-requests/{req['id']}", json={"decision": "deny"})).status_code == 409
    await phone.aclose()


async def test_history_from_other_hospitals_needs_consent_but_allergies_do_not(staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    enc = await folake_encounter(doctor)
    pid = await patient_id_of(enc["id"], doctor)
    lafenwa = await facility_id("Lafenwa")
    async with sessionmaker()() as db:
        db.add(PatientHistoryEntry(patient_id=pid, kind="condition", text="Asthma", facility_id=lafenwa))
        await db.commit()
    rec = (await doctor.get(f"/api/v1/hospital/encounters/{enc['id']}/record")).json()["data"]
    texts = [h["text"] for h in rec["history"]]
    assert "Asthma" not in texts and rec["hidden_from_other_hospitals"] == 1
    assert "Sulfonamides (Septrin)" in texts  # safety-critical: always visible

    phone = await folake_phone()
    token = (await phone.post("/api/v1/me/consents", json={})).json()["data"]["url"].split("/scan/")[1]
    await doctor.post("/api/v1/qr/redeem", json={"token": token})
    rec = (await doctor.get(f"/api/v1/hospital/encounters/{enc['id']}/record")).json()["data"]
    assert "Asthma" in [h["text"] for h in rec["history"]] and rec["hidden_from_other_hospitals"] == 0
    await phone.aclose()


async def test_share_from_a_referral(client, staff_client):
    from tests.conftest import DEMO_LOCATION, new_patient

    await new_patient(client)
    rid = (await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]["report_id"]
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    r = await client.post(f"/api/v1/me/referrals/{ref['id']}/share")
    assert r.status_code == 200 and r.json()["data"]["active"] is True
    # Another patient's phone cannot share someone else's referral
    other = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    await new_patient(other)
    assert (await other.post(f"/api/v1/me/referrals/{ref['id']}/share")).status_code == 404
    await other.aclose()
