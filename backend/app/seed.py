"""Synthetic demo seed. `python -m app.seed` wipes all data and reseeds in seconds.

Everything here is fictional: facility names carry "(Demo)", people and phone numbers are made up.
Logins are written to backend/var/DEMO_LOGINS.md (gitignored), never printed with passwords.
"""

import asyncio
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, text

from app.core.config import BACKEND_DIR
from app.core.db import Base, sessionmaker, utcnow
from app.core.security import hash_password
from app.engines.triage.data import care_types
from app.models import (
    Facility,
    FacilityService,
    Service,
    TriageReport,
    User,
    Verification,
    Vital,
    WorkerProfile,
)
from app.models.enums import Availability, Role, TriageStatus, VerificationStatus
from app.services.patients import create_patient
from app.services.uploads import store_bytes, upload_dir

A, L, U, K = Availability.available, Availability.limited, Availability.unavailable, Availability.unknown
FRESH, STALE, OLD = timedelta(hours=1), timedelta(hours=12), timedelta(days=4)

# Demo origin used by the demo script: Abeokuta South (Ibara / Kuto area).
DEMO_ORIGIN = (7.1475, 3.3619)


@dataclass
class F:
    slug: str
    name: str
    type: str
    lga: str
    lat: float
    lng: float
    phone: str
    services: dict  # code -> (availability, age-of-confirmation or None)
    status: str = VerificationStatus.approved
    demo_role: str = ""


FACILITIES = [
    F("ibara", "Ibara Family Clinic (Demo)", "clinic", "Abeokuta South", 7.1420, 3.3560, "+234 800 000 0101",
      {"general_doctor_on_duty": (A, FRESH), "lab": (A, FRESH), "oxygen": (L, FRESH), "emergency_unit": (A, FRESH)},
      demo_role="closest; no obstetrician -> excluded for pregnancy bleeding"),
    F("central", "Abeokuta Central Hospital (Demo)", "general", "Abeokuta South", 7.1600, 3.3480, "+234 800 000 0102",
      {"general_doctor_on_duty": (A, FRESH), "obstetrician_on_duty": (A, FRESH), "blood_bank": (A, FRESH),
       "theatre": (A, FRESH), "neonatal_unit": (A, FRESH), "emergency_unit": (A, FRESH), "oxygen": (A, FRESH),
       "lab": (A, FRESH), "xray": (A, FRESH), "surgeon_on_duty": (A, FRESH)},
      demo_role="ranked first for the demo case; doctor DECLINES (theatre busy)"),
    F("sapon", "Sapon Mother & Child Hospital (Demo)", "specialist", "Abeokuta South", 7.1550, 3.3850,
      "+234 800 000 0103",
      {"obstetrician_on_duty": (A, FRESH), "blood_bank": (A, FRESH), "theatre": (A, FRESH),
       "neonatal_unit": (A, FRESH), "emergency_unit": (A, FRESH), "paediatrician_on_duty": (A, FRESH),
       "oxygen": (A, FRESH), "lab": (A, FRESH), "general_doctor_on_duty": (A, FRESH)},
      demo_role="next ranked; ACCEPTS"),
    F("teaching", "Ogun Teaching Hospital (Demo)", "teaching", "Abeokuta North", 7.1700, 3.3650, "+234 800 000 0104",
      {"general_doctor_on_duty": (A, STALE), "obstetrician_on_duty": (A, STALE), "blood_bank": (L, STALE),
       "theatre": (A, STALE), "neonatal_unit": (A, STALE), "icu": (L, STALE), "emergency_unit": (A, STALE),
       "surgeon_on_duty": (A, STALE), "paediatrician_on_duty": (A, STALE), "oxygen": (A, STALE),
       "ecg": (A, STALE), "xray": (A, STALE), "lab": (A, STALE)},
      demo_role="big but availability is stale (12 h)"),
    F("lafenwa", "Lafenwa General Hospital (Demo)", "general", "Abeokuta North", 7.1700, 3.3300, "+234 800 000 0105",
      {"general_doctor_on_duty": (A, FRESH), "obstetrician_on_duty": (K, None), "blood_bank": (A, OLD),
       "theatre": (A, OLD), "oxygen": (A, FRESH), "lab": (A, FRESH), "isolation_ward": (A, FRESH)},
      demo_role="obstetrician availability unknown -> kept but labelled and scored lower"),
    F("kemta", "Kemta Primary Health Centre (Demo)", "phc", "Abeokuta South", 7.1380, 3.3700, "+234 800 000 0106",
      {"general_doctor_on_duty": (L, FRESH), "lab": (A, FRESH)}),
    F("obantoko", "Obantoko Specialist Hospital (Demo)", "specialist", "Odeda", 7.1950, 3.3950, "+234 800 000 0107",
      {"surgeon_on_duty": (A, FRESH), "theatre": (A, FRESH), "blood_bank": (A, FRESH), "xray": (A, FRESH),
       "emergency_unit": (A, FRESH), "obstetrician_on_duty": (U, FRESH), "general_doctor_on_duty": (A, FRESH),
       "icu": (A, FRESH), "oxygen": (A, FRESH)}),
    F("adigbe", "Adigbe Heart & Chest Centre (Demo)", "specialist", "Abeokuta South", 7.1200, 3.3800,
      "+234 800 000 0108",
      {"emergency_unit": (A, FRESH), "general_doctor_on_duty": (A, FRESH), "ecg": (A, FRESH), "oxygen": (A, FRESH),
       "icu": (L, FRESH), "lab": (A, FRESH), "xray": (A, FRESH)}),
    F("asero", "Asero Community Hospital (Demo)", "general", "Abeokuta South", 7.1300, 3.3400, "+234 800 000 0109",
      {"general_doctor_on_duty": (A, FRESH), "obstetrician_on_duty": (A, FRESH), "blood_bank": (A, FRESH),
       "theatre": (A, FRESH)},
      status=VerificationStatus.pending, demo_role="PENDING verification -> never appears in matching"),
]

HOSPITAL_ROLES = [Role.facility_admin, Role.receptionist, Role.nurse, Role.doctor, Role.lab]
FIRST_NAMES = ["Adaeze", "Tunde", "Bisi", "Chinedu", "Halima", "Segun", "Ngozi", "Ibrahim", "Kemi", "Emeka"]


def synthetic_pdf(title: str) -> bytes:
    """A tiny valid one-page PDF that says it is a synthetic demo document."""
    text = f"SYNTHETIC DEMO DOCUMENT - NOT A REAL LICENCE - {title}".replace("(", "[").replace(")", "]")
    stream = f"BT /F1 14 Tf 40 760 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>"),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def clear_uploads() -> None:
    for f in upload_dir().glob("*"):
        if f.is_file() and f.suffix in {".pdf", ".png", ".jpg"} and len(f.stem) == 32:
            f.unlink()


async def add_verification(db, subject_type, user, fac, status, reviewer, doc_title=None, details=None):
    docs = []
    if doc_title:
        kind = "facility_licence" if subject_type == "facility" else "worker_licence"
        up = store_bytes(synthetic_pdf(doc_title), f"{doc_title.lower().replace(' ', '-')}.pdf", kind,
                         user.id if user else None, fac.id if fac else None)
        db.add(up)
        await db.flush()
        docs = [str(up.id)]
    decided = status != VerificationStatus.pending
    db.add(Verification(subject_type=subject_type, subject_user_id=user.id if user else None,
                        subject_facility_id=fac.id if fac else None, status=status, documents=docs,
                        details=details or {}, reviewer_id=reviewer.id if decided else None,
                        decided_at=utcnow() - timedelta(days=30) if decided else None))


async def wipe(db) -> None:
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    await db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def seed(password: str | None = None, write_logins: bool = False) -> Path | None:
    password = password or os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(9)
    pw_hash = hash_password(password)
    now = utcnow()
    logins: list[tuple[str, str, str]] = []

    async with sessionmaker()() as db:
        await wipe(db)
        clear_uploads()

        for s in care_types()["services"]:
            db.add(Service(code=s["code"], name=s["name"], category=s["category"]))
        await db.flush()

        admin = User(email="admin@vitalis.demo", password_hash=pw_hash, full_name="Network Admin (Demo)",
                     role=Role.network_admin, status=VerificationStatus.approved)
        db.add(admin)
        logins.append(("Network admin", admin.email, "approved"))

        n = 0
        for f in FACILITIES:
            fac = Facility(name=f.name, type=f.type, lga=f.lga, lat=f.lat, lng=f.lng, phone=f.phone,
                           address=f"{f.lga}, Ogun State", status=f.status, licence_number=f"OG-HF-{1000 + n}")
            db.add(fac)
            await db.flush()
            for code, (avail, age) in f.services.items():
                db.add(FacilityService(facility_id=fac.id, service_code=code, availability_status=avail,
                                       last_confirmed_at=(now - age) if age else None))
            roles = HOSPITAL_ROLES if f.status == VerificationStatus.approved else [Role.facility_admin]
            for role in roles:
                n += 1
                email = f"{role.value.replace('_', '')}.{f.slug}@vitalis.demo"
                u = User(email=email, password_hash=pw_hash,
                         full_name=f"{FIRST_NAMES[n % len(FIRST_NAMES)]} ({role.value}, demo)",
                         role=role, facility_id=fac.id, licence_number=f"DEMO-{role.value[:3].upper()}-{n:04d}",
                         status=VerificationStatus.approved if f.status == VerificationStatus.approved
                         else VerificationStatus.pending)
                db.add(u)
                logins.append((f"{f.name} - {role.value}", email, u.status))
                if role == Role.facility_admin:
                    await db.flush()
                    await add_verification(db, "facility", u, fac, f.status, admin, f"Facility licence {fac.name}",
                                           {"licence_number": fac.licence_number,
                                            "services": list(f.services)})

        for i, (name, bname, status) in enumerate(
            [("Mama Tola (chemist, demo)", "Tola Patent Medicine Store", VerificationStatus.approved),
             ("Mr Okafor (chemist, demo)", "Okafor Chemist", VerificationStatus.approved),
             ("Pending Worker (demo)", "New PPMV Shop", VerificationStatus.pending)], start=1):
            email = f"chemist{i}@vitalis.demo"
            u = User(email=email, password_hash=pw_hash, full_name=name, role=Role.worker, status=status,
                     licence_number=f"PPMV-OG-{2000 + i}")
            db.add(u)
            await db.flush()
            db.add(WorkerProfile(user_id=u.id, worker_type="chemist", business_name=bname, lga="Abeokuta South",
                                 lat=DEMO_ORIGIN[0] + 0.002 * i, lng=DEMO_ORIGIN[1] - 0.002 * i))
            logins.append((f"Frontline worker {i}", email, status))
            await add_verification(db, "worker", u, None, status, admin, f"PPMV licence {name}",
                                   {"licence_number": u.licence_number, "worker_type": "chemist",
                                    "business_name": bname, "lga": "Abeokuta South"})

        # A staff member waiting for their facility admin at Central.
        central = (await db.execute(select(Facility).where(Facility.name == FACILITIES[1].name))).scalar_one()
        nurse = User(email="newnurse.central@vitalis.demo", password_hash=pw_hash, full_name="Funmi (new nurse, demo)",
                     role=Role.nurse, status=VerificationStatus.pending, facility_id=central.id,
                     licence_number="NMCN-DEMO-7781")
        db.add(nurse)
        await db.flush()
        db.add(Verification(subject_type="staff", subject_user_id=nurse.id, subject_facility_id=central.id,
                            details={"licence_number": nurse.licence_number, "role": "nurse"}))
        logins.append(("Central - pending nurse", nurse.email, "pending"))

        # Demo patients (synthetic). Recovery codes let a demo phone restore them.
        patients = []
        for display, age, sex, preg, phone in [
            ("Mrs. Adebayo (demo)", "adult", "female", True, "+2348000000001"),
            ("Baba Ogun (demo)", "elderly", "male", False, None),
            ("Little Ife (demo)", "under5", "female", False, "+2348000000003"),
        ]:
            p, _key, recovery = await create_patient(db, phone=phone, age_group=age, sex=sex, pregnant=preg,
                                                     display_name=display)
            patients.append((display, p, recovery))

        # A little history: an earlier antenatal check-in for Mrs. Adebayo with chemist vitals.
        _, adebayo, _ = patients[0]
        old = TriageReport(patient_id=adebayo.id, entry="other", status=TriageStatus.completed,
                           context={"age_group": "adult", "sex": "female", "pregnant": True},
                           answers={"symptoms": [{"code": "HEADACHE", "region": "head", "severity": 2,
                                                  "onset": "days"}], "regions": ["head"]},
                           action_level="see_chemist", care_type="obstetrics", lga="Abeokuta South",
                           rules_version="rf-2026-11-12.1")
        db.add(old)
        await db.flush()
        t = now - timedelta(days=9)
        for kind, value, unit in [("systolic_bp", 118, "mmHg"), ("diastolic_bp", 76, "mmHg"), ("pulse", 88, "bpm"),
                                  ("temp_c", 36.8, "°C"), ("spo2", 98, "%")]:
            db.add(Vital(patient_id=adebayo.id, report_id=old.id, source="worker", kind=kind, value=value, unit=unit,
                         measured_at=t))

        await db.commit()

    if not write_logins:
        return None
    out = BACKEND_DIR / "var" / "DEMO_LOGINS.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# VITALIS demo logins (synthetic, local only — do not commit)", "",
             f"Password for every account: `{password}`", "", "| Who | Email | Status |", "|---|---|---|"]
    lines += [f"| {who} | {email} | {status} |" for who, email, status in logins]
    lines += ["", "## Demo patients (restore on a phone via Recover)", "", "| Patient | VITALIS ID | Recovery code |",
              "|---|---|---|"]
    lines += [f"| {d} | {p.vitalis_id} | {rc} |" for d, p, rc in patients]
    lines += ["", "## Facility roles in the demo", ""]
    lines += [f"- **{f.name}**: {f.demo_role}" for f in FACILITIES if f.demo_role]
    out.write_text("\n".join(lines) + "\n")
    return out


if __name__ == "__main__":
    path = asyncio.run(seed(write_logins=True))
    print(f"Seeded. Logins written to {path}")
