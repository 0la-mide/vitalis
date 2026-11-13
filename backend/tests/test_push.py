"""Web Push: sign-up for patients and staff, alerts on referral events, dead subscriptions removed."""

import asyncio

from sqlalchemy import select

from app.core.db import sessionmaker
from app.models import PushSubscription
from app.services import push
from tests.conftest import DEMO_LOCATION, new_patient

SUB = {"endpoint": "https://push.example.test/abc", "keys": {"p256dh": "p" * 20, "auth": "a" * 10}}


async def _drain():
    while push._pending:
        await asyncio.gather(*list(push._pending))


async def test_key_and_subscriptions(client, staff_client):
    key = (await client.get("/api/v1/push/key")).json()["data"]["public_key"]
    assert len(key) > 80  # base64url of a 65-byte EC point

    await new_patient(client)
    assert (await client.post("/api/v1/me/push", json=SUB)).status_code == 200
    doctor = await staff_client("doctor.central@vitalis.demo")
    other = {**SUB, "endpoint": "https://push.example.test/doc"}
    assert (await doctor.post("/api/v1/push/subscribe", json=other)).status_code == 200
    # Plain http endpoints are refused.
    assert (await doctor.post("/api/v1/push/subscribe", json={**SUB, "endpoint": "http://x"})).status_code == 422
    async with sessionmaker()() as db:
        rows = (await db.execute(select(PushSubscription))).scalars().all()
    assert {(r.patient_id is not None, r.user_id is not None) for r in rows} == {(True, False), (False, True)}


async def test_family_and_hospital_alerted(client, staff_client, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(push, "_send_one", lambda e, p, a, payload: sent.append((e, payload)) or 201)

    await new_patient(client)
    await client.post("/api/v1/me/push", json=SUB)
    central = await staff_client("receptionist.central@vitalis.demo")
    await central.post("/api/v1/push/subscribe", json={**SUB, "endpoint": "https://push.example.test/desk"})

    rid = (await client.post("/api/v1/triage", json={"taps": [
        DEMO_LOCATION, {"kind": "emergency", "code": "pregnancy"}, {"kind": "region", "region": "pelvis"},
        {"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY", "region": "pelvis"}]})).json()["data"]["report_id"]
    ref = (await client.post(f"/api/v1/triage/{rid}/referral", json={})).json()["data"]
    await _drain()
    assert any(e.endswith("/desk") and "New referral" in p for e, p in sent)
    assert "bleeding" not in str(sent).lower()  # nothing clinical on a lock screen

    doctor = await staff_client("doctor.central@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    await _drain()
    assert any(e.endswith("/abc") and "ready" in p.lower() for e, p in sent)


async def test_gone_subscription_removed(client, monkeypatch):
    monkeypatch.setattr(push, "_send_one", lambda *a: 410)
    p = await new_patient(client)
    await client.post("/api/v1/me/push", json=SUB)
    async with sessionmaker()() as db:
        await push.notify(db, patient_ids=[p["patient_id"]], title="t", body="b", url="/")
    await _drain()
    async with sessionmaker()() as db:
        assert not (await db.execute(select(PushSubscription))).scalars().all()
