"""USSD from a basic phone: menus, the request reaching the clinic, the answer by SMS, and the ambulance line."""

import pytest

from app.core.config import get_settings
from app.seed import FACILITIES
from app.services import ussd
from app.services.notify import ConsoleSms
from tests.conftest import DEMO_LOCATION, new_patient

PHONE = "+2348031234567"


async def dial(client, text: str, phone: str = PHONE) -> str:
    r = await client.post("/api/v1/ussd", content=f"sessionId=s1&serviceCode=*384*8482%23&phoneNumber={phone.replace('+', '%2B')}&text={text}",
                          headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200, r.text
    return r.text


def test_every_menu_fits_a_ussd_screen():
    texts = ["", "1", "2", "1*7", "1*8", "2*1", "2*1*1"]
    for t in texts:
        menu = ussd.screen(ussd.read(t))
        assert menu and menu.startswith("CON ") and len(menu) <= ussd.MAX_SCREEN, (t, menu and len(menu))


def test_back_home_and_wrong_choices():
    assert ussd.read("1*0").state == "root"
    assert ussd.read("1*7*00").state == "root"
    st = ussd.read("1*9")
    assert st.state == "emergency" and st.error
    assert "Please choose" in ussd.screen(st)
    assert ussd.read("1*9*1").state == "area"  # the wrong answer is ignored, the right one taken


async def test_emergency_by_ussd_reaches_the_clinic_and_the_answer_comes_by_sms(client, staff_client):
    assert (await dial(client, "")).startswith("CON VITALIS: healthcare for everyone")
    assert "Pregnancy problem" in await dial(client, "1")
    assert "Bleeding" in await dial(client, "1*7")
    assert "Abeokuta South" in await dial(client, "1*7*1")
    ConsoleSms.sent.clear()
    end = await dial(client, "1*7*1*1")
    assert end.startswith("END Sent to") and "Ambulance: 08112000033" in end and len(end) <= ussd.MAX_SCREEN
    assert ConsoleSms.sent and ConsoleSms.sent[-1][0] == PHONE and "was sent to" in ConsoleSms.sent[-1][1]

    # The clinic sees it on Incoming, marked USSD, with the number to call back.
    name = end.removeprefix("END Sent to ").split(" (")[0]
    slug = next(f.slug for f in FACILITIES if f.name.startswith(name))
    doctor = await staff_client(f"doctor.{slug}@vitalis.demo")
    items = (await doctor.get("/api/v1/hospital/incoming")).json()["data"]
    item = next(i for i in items if i["channel"] == "ussd")
    assert item["callback_phone"] == PHONE and item["red_flag"] and item["care_type"] == "obstetrics"

    ConsoleSms.sent.clear()
    await doctor.patch(f"/api/v1/hospital/referrals/{item['id']}", json={"action": "accept"})
    assert any(to == PHONE and "is ready for" in m and "08112000033" in m for to, m in ConsoleSms.sent)

    # Dialling again: no duplicate request, just the status.
    again = await dial(client, "1*7*1*1")
    assert "is READY for you" in again
    assert "is READY for you" in await dial(client, "4")
    assert len([i for i in (await doctor.get("/api/v1/hospital/incoming")).json()["data"] if i["channel"] == "ussd"]) == 1


async def test_not_urgent_and_ambulance(client):
    end = await dial(client, "2*1*1*1", phone="+2348039990000")
    assert end.startswith("END ")
    amb = await dial(client, "3")
    assert "Ogun State Ambulance: 08112000033" in amb and "112" in amb
    assert (await dial(client, "4", phone="+2348039990001")).startswith("END You have no request yet")


async def test_triage_and_lines_show_the_ogun_ambulance(client):
    lines = (await client.get("/api/v1/lines")).json()["data"]
    assert lines["ambulances"] == [{"name": "Ogun State Ambulance", "number": "08112000033"}]
    assert lines["national"]["number"] == "112" and lines["ussd_code"]
    await new_patient(client)
    out = (await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]
    assert out["ambulance"]["number"] == "08112000033"
    far = (await client.post("/api/v1/triage", json={"taps": [{"kind": "location", "lat": 9.07, "lng": 7.49},
                                                              {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]
    assert far["ambulance"] is None  # Abuja: we don't know that ambulance yet, so we don't guess
    b = (await client.get("/api/v1/offline/bundle")).json()["data"]
    assert b["lines"]["ambulances"]["Ogun"]["number"] == "08112000033"


async def test_simulator_only_with_demo_numbers_and_never_sends_real_sms(client):
    bad = await client.post("/api/v1/demo/ussd", json={"phone": PHONE, "text": ""})
    assert bad.status_code == 422
    demo = "0000 000 0001"
    r = (await client.post("/api/v1/demo/ussd", json={"phone": demo, "text": "1*2*1"})).json()["data"]
    assert r["done"] and r["reply"].startswith("Sent to")
    inbox = (await client.get("/api/v1/demo/sms", params={"phone": demo})).json()["data"]
    assert inbox and "was sent to" in inbox[0]["text"]
    assert all(to != "+2340000000001" for to, _ in ConsoleSms.sent)


@pytest.fixture
def prod_settings():
    s = get_settings()
    old = (s.env, s.ussd_secret)
    yield s
    s.env, s.ussd_secret = old


async def test_gateway_needs_the_secret_in_prod(client, prod_settings):
    prod_settings.env = "prod"
    prod_settings.ussd_secret = ""
    r = await client.post("/api/v1/ussd", content="phoneNumber=%2B2348031234567&text=")
    assert r.status_code == 404
    prod_settings.ussd_secret = "s3cret"
    assert (await client.post("/api/v1/ussd?key=nope", content="phoneNumber=%2B2348031234567&text=")).status_code == 403
    ok = await client.post("/api/v1/ussd?key=s3cret", content="phoneNumber=%2B2348031234567&text=")
    assert ok.status_code == 200 and ok.text.startswith("CON")
