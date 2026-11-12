import importlib.util
import os
from pathlib import Path

os.environ["ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://vitalis:vitalis_dev@localhost:5432/vitalis_test"
)
# Tests TRUNCATE every table: refuse to run against anything that is not a test database.
assert os.environ["DATABASE_URL"].rsplit("/", 1)[-1].endswith("_test"), "TEST_DATABASE_URL must point at a *_test DB"
os.environ["MODEL_URL"] = "http://model-stub"
os.environ["DEMO_PASSWORD"] = "test-password-123"
# Keep test documents away from dev uploads.
os.environ["UPLOAD_DIR"] = str(Path(__file__).resolve().parents[1] / "var" / "test-uploads")

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import get_settings
from app.core.db import configure_engine
from app.engines.model_client import client as model_client

get_settings.cache_clear()
configure_engine(os.environ["DATABASE_URL"])

from app.main import app
from app.seed import seed

PASSWORD = "test-password-123"
_spec = importlib.util.spec_from_file_location(
    "model_stub", Path(__file__).resolve().parents[2] / "model" / "app.py"
)
model_stub = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model_stub)


@pytest.fixture(autouse=True)
def model_up():
    """By default the disease model is the in-process stub. Tests can stop it."""
    model_client._client = httpx.AsyncClient(transport=ASGITransport(app=model_stub.app))
    yield
    model_client._client = None


@pytest.fixture
def model_down():
    def fail(request):
        raise httpx.ConnectError("model stopped")

    model_client._client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
    yield


@pytest.fixture(autouse=True)
async def fresh_db():
    await seed(PASSWORD)
    yield


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def login(c: httpx.AsyncClient, email: str, password: str = PASSWORD) -> dict:
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    c.headers["x-csrf-token"] = r.json()["data"]["csrf_token"]
    return r.json()["data"]


@pytest.fixture
async def staff_client():
    """Factory: a fresh, logged-in client per email."""
    clients: list[httpx.AsyncClient] = []

    async def make(email: str) -> httpx.AsyncClient:
        c = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        clients.append(c)
        await login(c, email)
        return c

    yield make
    for c in clients:
        await c.aclose()


async def new_patient(c: httpx.AsyncClient) -> dict:
    r = await c.post("/api/v1/patients/start", json={})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    c.headers["x-patient-key"] = data["device_key"]
    return data


DEMO_LOCATION = {"kind": "location", "lat": 7.1475, "lng": 3.3619}
