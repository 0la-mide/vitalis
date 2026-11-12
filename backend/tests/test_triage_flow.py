import json

from tests.conftest import DEMO_LOCATION, new_patient

DISEASE_WORDS = ["haemorrhage", "ANTEPARTUM", "likelihood", "Malaria", "Pneumonia", "condition_code"]


async def test_patient_start_and_recover(client):
    p = await new_patient(client)
    assert p["vitalis_id"].startswith("VT-")
    old_key = p["device_key"]
    r = await client.post("/api/v1/patients/recover",
                          json={"vitalis_id": p["vitalis_id"], "recovery_code": p["recovery_code"]})
    assert r.status_code == 200
    new = r.json()["data"]
    assert new["device_key"] != old_key
    # old device key no longer works; recovery code is one-time
    client.headers["x-patient-key"] = old_key
    assert (await client.post("/api/v1/triage", json={"taps": []})).status_code == 401
    r2 = await client.post("/api/v1/patients/recover",
                           json={"vitalis_id": p["vitalis_id"], "recovery_code": p["recovery_code"]})
    assert r2.status_code == 401


async def test_patient_cannot_read_other_report(client):
    await new_patient(client)
    rid = (await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION]})).json()["data"]["report_id"]
    await new_patient(client)  # different device
    assert (await client.get(f"/api/v1/triage/{rid}")).status_code == 404


async def test_demo_path_red_flag_and_exclusion(client):
    """Pregnancy problem -> pelvis -> heavy bleeding: red flag, obstetrics, closest clinic excluded."""
    await new_patient(client)
    r = await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "pregnancy"}]})
    d = r.json()["data"]
    assert not d["red_flag"]["fired"]
    rid = d["report_id"]
    await client.post(f"/api/v1/triage/{rid}/taps", json={"taps": [{"kind": "region", "region": "pelvis"}]})
    r = await client.post(
        f"/api/v1/triage/{rid}/taps",
        json={"taps": [{"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY", "region": "pelvis"}]},
    )
    d = r.json()["data"]
    assert d["red_flag"]["fired"]
    assert d["action_level"] == "go_now"
    assert d["care_type"] == "obstetrics"
    assert d["heads_up_sent"]
    top_names = [h["name"] for h in d["hospitals"]["top"]]
    assert "Ibara Family Clinic (Demo)" not in top_names
    assert top_names[0] == "Abeokuta Central Hospital (Demo)"
    assert "Asero Community Hospital (Demo)" not in json.dumps(d)  # pending facility never shown
    excl = {e["name"]: e["reasons"] for e in d["hospitals"]["excluded"]}
    assert any("obstetrician" in reason.lower() for reason in excl["Ibara Family Clinic (Demo)"])
    for word in DISEASE_WORDS:
        assert word.lower() not in r.text.lower()


async def test_red_flag_fires_with_model_stopped(client, model_down):
    await new_patient(client)
    r = await client.post("/api/v1/triage", json={"taps": [{"kind": "emergency", "code": "cant_breathe"}]})
    d = r.json()["data"]
    assert r.status_code == 200
    assert d["red_flag"]["fired"] and d["action_level"] == "go_now"
    assert d["care_type"] == "respiratory"


async def test_non_urgent_path_uses_model_and_hides_names(client):
    await new_patient(client)
    rid = (await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION]})).json()["data"]["report_id"]
    r = await client.post(f"/api/v1/triage/{rid}/taps", json={"taps": [
        {"kind": "context", "age_group": "adult", "sex": "male"},
        {"kind": "region", "region": "whole_body"},
        {"kind": "symptom", "code": "FEVER"},
        {"kind": "severity", "value": 3},
        {"kind": "onset", "value": "days"},
    ]})
    d = r.json()["data"]
    assert not d["red_flag"]["fired"]
    assert d["care_type"] == "infectious_disease"  # from the stub model's malaria output
    assert d["action_level"] == "see_chemist"
    for word in DISEASE_WORDS:
        assert word.lower() not in r.text.lower()


async def test_model_down_falls_back_to_region(client, model_down):
    await new_patient(client)
    rid = (await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION]})).json()["data"]["report_id"]
    r = await client.post(f"/api/v1/triage/{rid}/taps", json={"taps": [
        {"kind": "region", "region": "legs"}, {"kind": "symptom", "code": "LIMB_PAIN"}]})
    assert r.json()["data"]["care_type"] == "trauma_surgery"


async def test_invalid_tap_rejected(client):
    await new_patient(client)
    rid = (await client.post("/api/v1/triage", json={"taps": []})).json()["data"]["report_id"]
    r = await client.post(f"/api/v1/triage/{rid}/taps", json={"taps": [{"kind": "symptom", "code": "NOPE"}]})
    assert r.status_code == 422
