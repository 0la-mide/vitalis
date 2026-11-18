"""Offline bundle, cost and coverage, NHIA preference, and the chemist's month."""

from tests.conftest import DEMO_LOCATION, new_patient


async def test_bundle_has_everything_to_triage_offline(client):
    r = await client.get("/api/v1/offline/bundle")
    assert r.status_code == 200
    assert "max-age" in r.headers["cache-control"]
    b = r.json()["data"]
    assert b["red_flags"]["rules"] and b["care"]["care_types"]["obstetrics"]["essential"]
    assert {e["code"] for e in b["emergencies"]} >= {"pregnancy", "cant_breathe"}
    names = {f["name"] for f in b["facilities"]}
    assert "Abeokuta Central Hospital (Demo)" in names
    assert "Asero Community Hospital (Demo)" not in names  # unverified facilities never leave the server
    central = next(f for f in b["facilities"] if f["name"].startswith("Abeokuta Central"))
    assert central["accepts_nhia"] and central["services"]["obstetrician_on_duty"]["status"]
    assert "model_code" not in str(b["taxonomy"])  # the disease model's vocabulary stays private


async def test_coverage_shown_and_set_by_hospital_admin(client, staff_client):
    doctor = await staff_client("doctor.ibara@vitalis.demo")
    assert (await doctor.get("/api/v1/hospital/coverage")).json()["data"]["accepts_nhia"] is False
    assert (await doctor.put("/api/v1/hospital/coverage", json={"accepts_nhia": True, "free_maternal_care": False})).status_code == 403
    admin = await staff_client("facilityadmin.ibara@vitalis.demo")
    r = await admin.put("/api/v1/hospital/coverage", json={"accepts_nhia": True, "free_maternal_care": True})
    assert r.json()["data"] == {"accepts_nhia": True, "free_maternal_care": True}
    cards = (await client.get("/api/v1/facilities")).json()["data"]
    assert next(c for c in cards if c["name"].startswith("Ibara"))["accepts_nhia"] is True


async def test_nhia_patients_see_nhia_hospitals_first_but_capability_still_rules(client):
    await new_patient(client)
    taps = [DEMO_LOCATION, {"kind": "emergency", "code": "pregnancy"}, {"kind": "region", "region": "pelvis"},
            {"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY", "region": "pelvis"}]
    plain = (await client.post("/api/v1/triage", json={"taps": taps})).json()["data"]["hospitals"]
    await client.patch("/api/v1/me/profile", json={"nhia_number": "NHIA/OG/0001"})
    insured = (await client.post("/api/v1/triage", json={"taps": taps})).json()["data"]["hospitals"]
    top = insured["top"][0]
    assert top["accepts_nhia"] and any("NHIA" in r for r in top["reasons"])
    assert all("NHIA" not in r for h in plain["top"] for r in h["reasons"])
    # A hospital without an obstetrician is still excluded, cover or not.
    assert any(e["name"].startswith("Ibara") for e in insured["excluded"])
    assert any("Free maternal" in r for r in top["reasons"]) or any(h["free_maternal_care"] for h in insured["top"])


async def test_chemist_month(staff_client):
    chemist = await staff_client("chemist1@vitalis.demo")
    s0 = (await chemist.get("/api/v1/worker/stats")).json()["data"]
    start = (await chemist.post("/api/v1/worker/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})).json()["data"]
    ref = (await chemist.post(f"/api/v1/worker/triage/{start['triage']['report_id']}/referral", json={})).json()["data"]
    s1 = (await chemist.get("/api/v1/worker/stats")).json()["data"]
    assert s1["patients_referred"] == s0["patients_referred"] + 1 and s1["emergencies"] == s0["emergencies"] + 1
    slug = ref["facility_name"].split()[0].lower()
    doctor = await staff_client(f"doctor.{slug}@vitalis.demo")
    await doctor.patch(f"/api/v1/hospital/referrals/{ref['id']}", json={"action": "accept"})
    desk = await staff_client(f"receptionist.{slug}@vitalis.demo")
    await desk.post(f"/api/v1/hospital/referrals/{ref['id']}/arrived")
    s2 = (await chemist.get("/api/v1/worker/stats")).json()["data"]
    assert s2["reached_hospital"] == s1["reached_hospital"] + 1
    assert any("Lifesaver" in b for b in s2["badges"])
