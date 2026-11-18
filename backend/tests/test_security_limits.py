"""Rate limits and lockouts, switched on for these tests (the rest of the suite runs with them off)."""

import pytest

from app.core import guard
from app.core.ratelimit import limiter


@pytest.fixture
def limits_on(monkeypatch):
    monkeypatch.setattr(guard, "enabled", lambda: True)
    monkeypatch.setattr(guard, "login_failures", guard.Window(limit=8, seconds=900))
    monkeypatch.setattr(guard, "api_requests", guard.Window(limit=600, seconds=60))
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


async def test_wrong_passwords_lock_the_account_not_the_network(client, limits_on):
    from tests.conftest import PASSWORD

    email = "doctor.central@vitalis.demo"
    for _ in range(8):
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
        assert r.status_code == 401
    locked = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert locked.status_code == 429 and locked.json()["error"]["code"] == "too_many_attempts"
    # Someone else on the same network can still sign in.
    other = await client.post("/api/v1/auth/login", json={"email": "nurse.central@vitalis.demo", "password": PASSWORD})
    assert other.status_code == 200


async def test_a_good_login_clears_the_count(client, limits_on):
    from tests.conftest import PASSWORD

    email = "doctor.central@vitalis.demo"
    for _ in range(7):
        await client.post("/api/v1/auth/login", json={"email": email, "password": "nope-nope"})
    assert (await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})).status_code == 200
    for _ in range(7):
        await client.post("/api/v1/auth/login", json={"email": email, "password": "nope-nope"})
    assert (await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})).status_code == 200


async def test_rate_limited_requests_get_the_normal_error_shape(client, limits_on):
    body = {"vitalis_id": "VT-0000-00", "recovery_code": "AAAA-AAAA-AAAA"}
    codes = [(await client.post("/api/v1/patients/recover", json=body)).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    r = await client.post("/api/v1/patients/recover", json=body)
    assert r.json()["error"]["code"] == "rate_limited" and r.headers["retry-after"]


async def test_every_route_has_a_default_limit(client, limits_on):
    for _ in range(600):
        assert (await client.get("/api/v1/lines")).status_code == 200
    assert (await client.get("/api/v1/lines")).status_code == 429


async def test_ussd_simulator_cannot_flood_hospitals(client, limits_on, monkeypatch):
    monkeypatch.setattr(guard, "ussd_requests", guard.Window(limit=2, seconds=3600))
    for n in (1, 2):
        r = await client.post("/api/v1/demo/ussd", json={"phone": f"0000 000 010{n}", "text": "1*2*1"})
        assert r.status_code == 200, r.text
    blocked = await client.post("/api/v1/demo/ussd", json={"phone": "0000 000 0103", "text": "1*2*1"})
    assert blocked.status_code == 429
    # Browsing the menus is still fine.
    assert (await client.post("/api/v1/demo/ussd", json={"phone": "0000 000 0103", "text": "1"})).status_code == 200
