import json

from app.seed import synthetic_pdf
from tests.conftest import DEMO_LOCATION, login, new_patient

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PW = "a-long-password-1"


def facility_form(email="newadmin@clinic.demo", **over):
    data = {
        "facility_name": "Oke-Ilewo Women's Clinic (Demo)",
        "facility_type": "specialist",
        "lga": "Abeokuta South",
        "address": "Oke-Ilewo, Abeokuta",
        "facility_phone": "+234 800 000 0200",
        "lat": "7.1450",
        "lng": "3.3600",
        "facility_licence_number": "OG-HF-9001",
        "services": "obstetrician_on_duty,blood_bank,theatre",
        "full_name": "Dr Clinic Admin",
        "email": email,
        "password": PW,
    }
    data.update(over)
    return data


def worker_form(email="newchemist@ppmv.demo"):
    return {
        "full_name": "Iya Bisi",
        "email": email,
        "password": PW,
        "worker_type": "chemist",
        "licence_number": "PPMV-OG-7777",
        "business_name": "Bisi Medicine Store",
        "lga": "Abeokuta North",
    }


def pdf_file(name="licence.pdf"):
    return {"document": (name, synthetic_pdf("test"), "application/pdf")}


async def test_register_facility_pending_until_approved(client, staff_client):
    r = await client.post("/api/v1/auth/register/facility", data=facility_form(), files=pdf_file())
    assert r.status_code == 200, r.text
    fac_id = r.json()["data"]["facility_id"]

    # The new admin can sign in but only sees status.
    await login(client, "newadmin@clinic.demo", PW)
    me = (await client.get("/api/v1/auth/me")).json()["data"]
    assert me["status"] == "pending" and me["facility"]["status"] == "pending"
    assert (await client.get("/api/v1/hospital/incoming")).status_code == 403

    # Not in matching / public lists while pending.
    assert fac_id not in json.dumps((await client.get("/api/v1/facilities")).json())
    assert fac_id not in json.dumps((await client.get("/api/v1/auth/register/facilities")).json())

    admin = await staff_client("admin@vitalis.demo")
    queue = (await admin.get("/api/v1/admin/verifications?kind=facility")).json()["data"]
    item = next(v for v in queue if v["facility_id"] == fac_id)
    assert item["documents"] and item["details"]["licence_number"] == "OG-HF-9001"
    r = await admin.patch(f"/api/v1/admin/verifications/{item['id']}", json={"decision": "approve"})
    assert r.json()["data"]["status"] == "approved"

    me = (await client.get("/api/v1/auth/me")).json()["data"]
    assert me["status"] == "approved" and me["facility"]["status"] == "approved"
    assert (await client.get("/api/v1/hospital/services")).status_code == 200
    assert fac_id in json.dumps((await client.get("/api/v1/facilities")).json())


async def test_upload_validation(client):
    bad = {"document": ("licence.pdf", b"MZ\x90\x00 not a pdf", "application/pdf")}
    r = await client.post("/api/v1/auth/register/worker", data=worker_form(), files=bad)
    assert r.status_code == 415
    big = {"document": ("big.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024 + 10), "application/pdf")}
    r = await client.post("/api/v1/auth/register/worker", data=worker_form(), files=big)
    assert r.status_code == 413
    png = {"document": ("photo.png", PNG, "image/png")}
    r = await client.post("/api/v1/auth/register/worker", data=worker_form(), files=png)
    assert r.status_code == 200


async def test_duplicate_email_and_weak_password(client):
    r = await client.post("/api/v1/auth/register/worker", data=worker_form("chemist1@vitalis.demo"), files=pdf_file())
    assert r.status_code == 409
    form = worker_form("x@y.demo")
    form["password"] = "short"
    assert (await client.post("/api/v1/auth/register/worker", data=form, files=pdf_file())).status_code == 422


async def test_worker_reject_resubmit_approve(client, staff_client):
    r = await client.post("/api/v1/auth/register/worker", data=worker_form(), files=pdf_file())
    uid = r.json()["data"]["user_id"]
    admin = await staff_client("admin@vitalis.demo")
    v = next(x for x in (await admin.get("/api/v1/admin/verifications?kind=worker")).json()["data"]
             if x["user_id"] == uid)
    assert (await admin.patch(f"/api/v1/admin/verifications/{v['id']}", json={"decision": "reject"})).status_code == 422
    await admin.patch(f"/api/v1/admin/verifications/{v['id']}",
                      json={"decision": "reject", "reason": "Licence photo unreadable"})

    await login(client, "newchemist@ppmv.demo", PW)
    me = (await client.get("/api/v1/auth/me")).json()["data"]
    assert me["status"] == "rejected" and me["status_reason"] == "Licence photo unreadable"
    r = await client.post("/api/v1/auth/resubmit", data={"licence_number": "PPMV-OG-7778"}, files=pdf_file("new.pdf"))
    assert r.status_code == 200
    assert (await client.get("/api/v1/auth/me")).json()["data"]["status"] == "pending"

    v2 = next(x for x in (await admin.get("/api/v1/admin/verifications?kind=worker")).json()["data"]
              if x["user_id"] == uid)
    assert v2["id"] != v["id"] and v2["details"]["licence_number"] == "PPMV-OG-7778"
    await admin.patch(f"/api/v1/admin/verifications/{v2['id']}", json={"decision": "approve"})
    assert (await client.get("/api/v1/auth/me")).json()["data"]["status"] == "approved"


async def test_staff_registration_and_facility_admin_approval(client, staff_client):
    facs = (await client.get("/api/v1/auth/register/facilities")).json()["data"]
    central = next(f for f in facs if f["name"].startswith("Abeokuta Central"))
    sapon = next(f for f in facs if f["name"].startswith("Sapon"))
    body = {"full_name": "Dr New Doctor", "email": "newdoc@central.demo", "password": PW,
            "facility_id": central["id"], "role": "doctor", "licence_number": "MDCN-12345"}
    r = await client.post("/api/v1/auth/register/staff", json=body)
    assert r.status_code == 200
    uid = r.json()["data"]["user_id"]

    # Cannot register as facility_admin or under an unverified facility.
    assert (await client.post("/api/v1/auth/register/staff",
                              json={**body, "email": "a@b.demo", "role": "facility_admin"})).status_code == 422

    # Network admin does not see staff in its queue; Sapon's admin cannot touch Central's staff.
    admin = await staff_client("admin@vitalis.demo")
    assert uid not in json.dumps((await admin.get("/api/v1/admin/verifications?status=all")).json())
    sapon_admin = await staff_client("facilityadmin.sapon@vitalis.demo")
    assert (await sapon_admin.patch(f"/api/v1/hospital/staff/{uid}", json={"decision": "approve"})).status_code == 404
    assert uid not in json.dumps((await sapon_admin.get("/api/v1/hospital/staff")).json())

    # Doctors cannot approve staff.
    doctor = await staff_client("doctor.central@vitalis.demo")
    assert (await doctor.get("/api/v1/hospital/staff")).status_code == 403

    central_admin = await staff_client("facilityadmin.central@vitalis.demo")
    rows = (await central_admin.get("/api/v1/hospital/staff")).json()["data"]
    assert any(r["user_id"] == uid and r["status"] == "pending" for r in rows)
    r = await central_admin.patch(f"/api/v1/hospital/staff/{uid}", json={"decision": "approve"})
    assert any(x["user_id"] == uid and x["status"] == "approved" for x in r.json()["data"])
    assert sapon["id"] != central["id"]


async def test_suspend_blocks_work(client, staff_client):
    central_admin = await staff_client("facilityadmin.central@vitalis.demo")
    nurse = next(r for r in (await central_admin.get("/api/v1/hospital/staff")).json()["data"]
                 if r["email"] == "nurse.central@vitalis.demo")
    r = await central_admin.patch(f"/api/v1/hospital/staff/{nurse['user_id']}",
                                  json={"decision": "suspend", "reason": "Left the hospital"})
    assert r.status_code == 200
    c = await staff_client("nurse.central@vitalis.demo")
    assert (await c.get("/api/v1/hospital/incoming")).status_code == 403
    assert (await c.get("/api/v1/auth/me")).json()["data"]["status"] == "suspended"


async def test_suspended_facility_leaves_matching(client, staff_client):
    admin = await staff_client("admin@vitalis.demo")
    v = next(x for x in (await admin.get("/api/v1/admin/verifications?status=approved&kind=facility")).json()["data"]
             if x["facility_name"].startswith("Abeokuta Central"))
    await admin.patch(f"/api/v1/admin/verifications/{v['id']}", json={"decision": "suspend", "reason": "Licence lapsed"})
    await new_patient(client)
    r = await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "pregnancy"},
                                                            {"kind": "region", "region": "pelvis"},
                                                            {"kind": "symptom", "code": "BLEEDING_VAGINAL_HEAVY"}]})
    assert "Abeokuta Central" not in r.text
    doctor = await staff_client("doctor.central@vitalis.demo")
    assert (await doctor.get("/api/v1/hospital/incoming")).status_code == 403


async def test_documents_are_private(client, staff_client):
    admin = await staff_client("admin@vitalis.demo")
    v = (await admin.get("/api/v1/admin/verifications?kind=worker")).json()["data"][0]
    doc_id = v["documents"][0]["id"]
    r = await admin.get(f"/api/v1/admin/documents/{doc_id}")
    assert r.status_code == 200 and r.content.startswith(b"%PDF-")
    assert "sandbox" in r.headers["content-security-policy"]

    for email in ("doctor.central@vitalis.demo", "facilityadmin.central@vitalis.demo", "chemist1@vitalis.demo"):
        c = await staff_client(email)
        assert (await c.get(f"/api/v1/admin/documents/{doc_id}")).status_code == 404
    assert (await client.get(f"/api/v1/admin/documents/{doc_id}")).status_code == 401

    audit = (await admin.get("/api/v1/admin/audit?action=document.view")).json()["data"]
    assert audit and audit[0]["subject_id"] == doc_id


async def test_admin_only_endpoints(staff_client):
    for email in ("facilityadmin.central@vitalis.demo", "doctor.central@vitalis.demo", "chemist1@vitalis.demo"):
        c = await staff_client(email)
        assert (await c.get("/api/v1/admin/verifications")).status_code == 403
        assert (await c.get("/api/v1/admin/audit")).status_code == 403
        assert (await c.get("/api/v1/admin/metrics")).status_code == 403


async def test_audit_and_metrics(client, staff_client):
    await new_patient(client)
    await client.post("/api/v1/triage", json={"taps": [DEMO_LOCATION, {"kind": "emergency", "code": "cant_breathe"}]})
    admin = await staff_client("admin@vitalis.demo")
    m = (await admin.get("/api/v1/admin/metrics")).json()["data"]
    assert m["triage_reports"] >= 1 and m["red_flags"] >= 1
    assert m["facilities_pending"] == 1 and m["workers_pending"] == 1

    v = (await admin.get("/api/v1/admin/verifications?kind=worker")).json()["data"][0]
    await admin.patch(f"/api/v1/admin/verifications/{v['id']}", json={"decision": "approve"})
    page = (await admin.get("/api/v1/admin/audit?action=verification.&limit=5")).json()
    assert page["meta"]["total"] >= 1
    assert page["data"][0]["action"] == "verification.approve"
    assert page["data"][0]["actor_name"] == "Network Admin (Demo)"
