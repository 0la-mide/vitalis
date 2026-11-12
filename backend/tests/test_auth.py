import uuid

from fastapi import Depends

from app.core.deps import require_hospital_staff
from app.main import app
from app.models.enums import Role
from tests.conftest import PASSWORD, login

DOCTOR_ONLY = "/api/v1/_test/doctor-only"


@app.get(DOCTOR_ONLY)
async def _doctor_only(user=Depends(require_hospital_staff(Role.doctor))):
    return {"ok": True}


async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["database"] == "ok"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "x-request-id" in r.headers


async def test_login_sets_httponly_cookies(client):
    r = await client.post("/api/v1/auth/login", json={"email": "doctor.central@vitalis.demo", "password": PASSWORD})
    assert r.status_code == 200
    cookies = r.headers.get_list("set-cookie")
    access = next(c for c in cookies if c.startswith("vt_access="))
    csrf = next(c for c in cookies if c.startswith("vt_csrf="))
    assert "HttpOnly" in access and "SameSite=lax" in access
    assert "HttpOnly" not in csrf
    assert r.json()["data"]["role"] == "doctor"


async def test_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={"email": "doctor.central@vitalis.demo", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


async def test_unknown_user_same_error(client):
    r = await client.post("/api/v1/auth/login", json={"email": "ghost@vitalis.demo", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


async def test_csrf_required_on_mutation(staff_client):
    c = await staff_client("doctor.central@vitalis.demo")
    services = (await c.get("/api/v1/hospital/services")).json()["data"]
    del c.headers["x-csrf-token"]
    r = await c.patch(f"/api/v1/hospital/services/{services[0]['id']}", json={"availability_status": "limited"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_failed"


async def test_pending_worker_sees_only_status(staff_client):
    c = await staff_client("chemist3@vitalis.demo")
    me = await c.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["data"]["status"] == "pending"
    r = await c.get("/api/v1/hospital/incoming")
    assert r.status_code == 403


async def test_pending_facility_admin_blocked(staff_client):
    c = await staff_client("facilityadmin.asero@vitalis.demo")
    assert (await c.get("/api/v1/hospital/incoming")).status_code == 403
    assert (await c.get("/api/v1/hospital/services")).status_code == 403


async def test_nurse_cannot_call_doctor_only(staff_client):
    nurse = await staff_client("nurse.central@vitalis.demo")
    doctor = await staff_client("doctor.central@vitalis.demo")
    assert (await nurse.get(DOCTOR_ONLY)).status_code == 403
    assert (await doctor.get(DOCTOR_ONLY)).status_code == 200


async def test_receptionist_cannot_accept_referral(staff_client):
    c = await staff_client("receptionist.central@vitalis.demo")
    r = await c.patch(f"/api/v1/hospital/referrals/{uuid.uuid4()}", json={"action": "accept"})
    assert r.status_code == 403


async def test_worker_cannot_reach_hospital_routes(staff_client):
    c = await staff_client("chemist1@vitalis.demo")
    assert (await c.get("/api/v1/hospital/incoming")).status_code == 403


async def test_unauthenticated(client):
    assert (await client.get("/api/v1/hospital/incoming")).status_code == 401


async def test_logout_clears(client):
    await login(client, "doctor.central@vitalis.demo")
    r = await client.post("/api/v1/auth/logout")
    assert any(c.startswith("vt_access=") for c in r.headers.get_list("set-cookie"))
