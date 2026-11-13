"""One-tap demo sign-in: seeded @vitalis.demo accounts and demo patients only, and off in prod by default."""

from app.core.config import get_settings
from tests.conftest import new_patient


async def test_demo_accounts_and_one_tap_login(client):
    r = await client.get("/api/v1/demo/accounts")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    emails = {s["email"] for s in d["staff"]}
    assert {"admin@vitalis.demo", "doctor.central@vitalis.demo", "chemist1@vitalis.demo"} <= emails
    assert any(p["name"].startswith("Mrs. Folake") for p in d["patients"])
    assert all("password" not in str(s) for s in d["staff"])

    r = await client.post("/api/v1/demo/login", json={"email": "Doctor.Central@vitalis.demo"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["role"] == "doctor"
    client.headers["x-csrf-token"] = r.json()["data"]["csrf_token"]
    assert (await client.get("/api/v1/hospital/encounters")).status_code == 200


async def test_demo_login_refuses_non_demo_accounts(client):
    # A real (non-demo) registration must never be reachable through the demo door.
    r = await client.post("/api/v1/demo/login", json={"email": "someone@hospital.ng"})
    assert r.status_code == 404


async def test_demo_patient_opens_record_without_rotating_recovery(client):
    folake = next(p for p in (await client.get("/api/v1/demo/accounts")).json()["data"]["patients"]
                  if p["name"].startswith("Mrs. Folake"))
    r = await client.post("/api/v1/demo/patient", json={"vitalis_id": folake["vitalis_id"].lower()})
    assert r.status_code == 200, r.text
    client.headers["x-patient-key"] = r.json()["data"]["device_key"]
    rec = await client.get("/api/v1/me/records")
    assert rec.status_code == 200, rec.text

    # A patient who registered themselves is not a demo patient.
    other = await new_patient(client)
    assert (await client.post("/api/v1/demo/patient", json={"vitalis_id": other["vitalis_id"]})).status_code == 404


async def test_demo_logins_can_be_switched_off(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "demo_logins", False)
    assert (await client.get("/api/v1/demo/accounts")).status_code == 404
    assert (await client.post("/api/v1/demo/login", json={"email": "admin@vitalis.demo"})).status_code == 404
