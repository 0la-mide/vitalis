"""Demo patients: open a seeded demo patient's phone in one tap. Staff always sign in with email + password."""

from app.core.config import get_settings
from tests.conftest import new_patient


async def test_demo_patients_listed_without_staff(client):
    r = await client.get("/api/v1/demo/accounts")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert any(p["name"].startswith("Mrs. Folake") for p in d["patients"])
    assert "staff" not in d
    # No password-free staff sign-in.
    assert (await client.post("/api/v1/demo/login", json={"email": "admin@vitalis.demo"})).status_code in (404, 405)


async def test_demo_patient_opens_record_without_rotating_recovery(client):
    folake = next(p for p in (await client.get("/api/v1/demo/accounts")).json()["data"]["patients"]
                  if p["name"].startswith("Mrs. Folake"))
    r = await client.post("/api/v1/demo/patient", json={"vitalis_id": folake["vitalis_id"].lower()})
    assert r.status_code == 200, r.text
    client.headers["x-patient-key"] = r.json()["data"]["device_key"]
    assert (await client.get("/api/v1/me/records")).status_code == 200

    # A patient who registered themselves is not a demo patient.
    other = await new_patient(client)
    assert (await client.post("/api/v1/demo/patient", json={"vitalis_id": other["vitalis_id"]})).status_code == 404


async def test_demo_patients_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_logins", False)
    assert (await client.get("/api/v1/demo/accounts")).status_code == 404
