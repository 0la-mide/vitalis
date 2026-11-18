"""The network admin console: overview, accounts, devices, models, audit search and export."""

from tests.conftest import DEMO_LOCATION, PASSWORD, new_patient

SUB = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc123", "keys": {"p256dh": "k" * 40, "auth": "a" * 16}}
ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"


async def test_only_the_network_admin_sees_the_console(client, staff_client):
    doctor = await staff_client("doctor.central@vitalis.demo")
    for path in ("overview", "accounts", "devices", "models", "audit.csv"):
        assert (await doctor.get(f"/api/v1/admin/console/{path}")).status_code == 403
        assert (await client.get(f"/api/v1/admin/console/{path}")).status_code == 401


async def test_overview_counts_every_channel_and_day(client, staff_client):
    await new_patient(client)
    await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})
    await client.post("/api/v1/ussd", content="phoneNumber=%2B2348031110000&text=1*2*1")
    chemist = await staff_client("chemist1@vitalis.demo")
    await chemist.post("/api/v1/worker/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "accident"}]})

    admin = await staff_client("admin@vitalis.demo")
    o = (await admin.get("/api/v1/admin/console/overview?days=7")).json()["data"]
    assert len(o["series"]) == 7
    assert o["requests_by_channel"].get("app", 0) >= 1 and o["requests_by_channel"]["ussd"] >= 1
    assert o["requests_by_channel"]["chemist"] >= 1
    today = o["series"][-1]
    assert today["app"] >= 1 and today["ussd"] >= 1 and today["chemist"] >= 1 and today["emergencies"] >= 3
    assert today["sign_ins"] >= 2 and o["patients_by_ussd"] >= 1 and o["patients_active_24h"] >= 1
    assert o["accounts_by_role"]["doctor"] >= 1 and o["funnel"]["referred"] >= 1
    assert "VT-" not in str(o)  # counts only, no patient IDs


async def test_accounts_search_and_sign_in_counts(staff_client):
    admin = await staff_client("admin@vitalis.demo")
    await staff_client("doctor.central@vitalis.demo")
    r = (await admin.get("/api/v1/admin/console/accounts", params={"q": "doctor.central", "role": "doctor"})).json()
    row = r["data"][0]
    assert r["meta"]["total"] == 1 and row["email"] == "doctor.central@vitalis.demo"
    assert row["facility"].startswith("Abeokuta Central") and row["sign_ins_30d"] >= 1 and row["last_login_at"]
    chemists = (await admin.get("/api/v1/admin/console/accounts", params={"role": "worker"})).json()["data"]
    assert any(c["business"] for c in chemists)


async def test_devices_show_browsers_without_naming_patients(client, staff_client):
    await new_patient(client)
    await client.post("/api/v1/me/push", json=SUB, headers={"user-agent": ANDROID})
    doctor = await staff_client("doctor.central@vitalis.demo")
    await doctor.post("/api/v1/push/subscribe", json={**SUB, "endpoint": "https://web.push.apple.com/xyz"},
                      headers={"user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1"})
    admin = await staff_client("admin@vitalis.demo")
    d = (await admin.get("/api/v1/admin/console/devices")).json()["data"]
    assert d["alerts_patients"] == 1 and d["alerts_staff"] == 1
    assert d["by_browser"] == {"Chrome": 1, "Safari": 1} and d["by_os"] == {"Android": 1, "iPhone / iPad": 1}
    owners = {r["owner"] for r in d["recent"]}
    assert "Patient phone" in owners and any(o.startswith("doctor ·") for o in owners)
    assert d["phones_with_card"] >= 1 and d["phones_active_24h"] >= 1


async def test_models_report_health_speed_and_failures(client, staff_client, model_down):
    await new_patient(client)
    await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "context", "age_group": "adult", "sex": "male"},
                                                       {"kind": "region", "region": "head"},
                                                       {"kind": "symptom", "code": "HEADACHE", "region": "head"}]})
    admin = await staff_client("admin@vitalis.demo")
    m = (await admin.get("/api/v1/admin/console/models")).json()["data"]
    assert m["triage_calls"] >= 1 and m["triage_ok_rate"] is not None and m["triage_ok_rate"] < 1
    assert m["triage_last_error"] and len(m["series"]) == 14
    assert isinstance(m["service_up"], bool) and "ai_by_action" in m


async def test_audit_search_by_person_and_csv_export(staff_client):
    await staff_client("doctor.central@vitalis.demo")
    admin = await staff_client("admin@vitalis.demo")
    found = (await admin.get("/api/v1/admin/audit", params={"who": "doctor.central", "action": "auth.login"})).json()
    assert found["meta"]["total"] >= 1 and all(r["action"] == "auth.login" for r in found["data"])
    patients_only = (await admin.get("/api/v1/admin/audit", params={"actor_type": "patient"})).json()["data"]
    assert all(r["actor_type"] == "patient" and r["actor_name"] is None for r in patients_only)
    csv = await admin.get("/api/v1/admin/console/audit.csv", params={"action": "auth."})
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv")
    assert "attachment" in csv.headers["content-disposition"]
    lines = csv.text.strip().splitlines()
    assert lines[0].startswith("time_utc,action") and any("doctor.central@vitalis.demo" in line for line in lines)
    # The export itself is in the audit log.
    exp = (await admin.get("/api/v1/admin/audit", params={"action": "audit.export"})).json()["data"]
    assert exp and exp[0]["actor_name"]
    assert PASSWORD not in csv.text
