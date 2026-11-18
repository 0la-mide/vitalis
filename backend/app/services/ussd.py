"""USSD: healthcare for everyone. Any phone, no data, no app.

Someone dials the VITALIS code (e.g. *384*8482#) and answers numbered menus. Their answers become the same triage
taps the app sends, so the same red-flag rules and matching decide; the request lands on the clinic's Incoming
screen like any other, marked as dialled by USSD with a number to call back. The clinic's answer (accept or
decline) reaches them by SMS. No GPS on a basic phone, so they pick their local government area instead.

The gateway sends the whole session each time as text like "1*7*2*4" (Africa's Talking style), so nothing is
stored between screens. "0" goes back one step and "00" goes to the start. Every screen fits in 182 characters.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.db import utcnow
from app.models import Facility, Patient, Referral, TriageReport
from app.models.enums import ReferralStatus
from app.services import lines
from app.services import referrals as rsvc
from app.services import triage as tsvc
from app.services.notify import sms, to_international
from app.services.patients import create_patient

log = logging.getLogger("vitalis.ussd")

MAX_SCREEN = 182
REPEAT_WINDOW = timedelta(hours=2)  # one open request per phone in this window: no duplicate alerts to clinics

# (label, emergency code, follow-up question or None)
PREGNANCY = [("Bleeding", "BLEEDING_VAGINAL_HEAVY", "pelvis"), ("Strong labour pains", "LABOUR_PAINS", "lower_abdomen"),
             ("Water broke", "WATER_BROKEN", "pelvis"), ("Baby not moving", "REDUCED_FETAL_MOVEMENT", "lower_abdomen"),
             ("Fits", "SEIZURE", "whole_body")]
CHILD = [("Not drinking", "NOT_DRINKING", "whole_body"), ("Very sleepy", "LETHARGIC", "whole_body"),
         ("Fits", "SEIZURE", "whole_body"), ("Very hot body", "HIGH_FEVER", "whole_body"),
         ("Hard to breathe", "BREATHING_DIFFICULTY", "chest")]
EMERGENCIES: list[tuple[str, str, list | None]] = [
    ("Heavy bleeding", "heavy_bleeding", None), ("Can't breathe", "cant_breathe", None),
    ("Unconscious", "unconscious", None), ("Chest pain", "chest_pain", None), ("Fits", "seizure", None),
    ("Accident", "accident", None), ("Pregnancy problem", "pregnancy", PREGNANCY),
    ("Child very sick", "child_sick", CHILD),
]
PROBLEMS = [("Fever", "FEVER", "whole_body"), ("Cough", "COUGH", "chest"), ("Diarrhoea", "DIARRHOEA", "lower_abdomen"),
            ("Vomiting", "VOMITING", "upper_abdomen"), ("Belly pain", "ABDOMINAL_PAIN", "lower_abdomen"),
            ("Wound", "WOUND", "skin"), ("Rash", "RASH", "skin")]
WHO = [("Man", {"age_group": "adult", "sex": "male"}), ("Woman", {"age_group": "adult", "sex": "female"}),
       ("Pregnant woman", {"age_group": "adult", "sex": "female", "pregnant": True}),
       ("Child under 5", {"age_group": "under5"}), ("Child 5-12", {"age_group": "child"}),
       ("Older person", {"age_group": "elderly"})]

STATUS_WORDS = {
    ReferralStatus.pending: "has your request. Wait for their SMS",
    ReferralStatus.more_info: "has your request. Wait for their SMS",
    ReferralStatus.accepted: "is READY for you. Go now",
    ReferralStatus.overdue: "is still expecting you",
    ReferralStatus.arrived: "says you arrived",
    ReferralStatus.completed: "has finished your visit",
    ReferralStatus.declined: "could not take you",
    ReferralStatus.cancelled: "request was cancelled",
}


def _lgas() -> list[str]:
    return [r["name"] for r in tsvc.lgas()["lgas"]]


def _menu(title: str, options: list[str], back: bool = True) -> str:
    body = "\n".join(f"{i} {o}" for i, o in enumerate(options, start=1))
    return f"CON {title}\n{body}" + ("\n0 Back" if back else "")


ROOT = _menu("VITALIS: healthcare for everyone", ["Emergency", "Not urgent: find a clinic", "Call an ambulance",
                                                    "My last request"], back=False)


# ---------- reading the session ----------
@dataclass
class Session:
    state: str = "root"
    ans: dict = field(default_factory=dict)
    error: bool = False


def _pick(seg: str, n: int) -> int | None:
    return int(seg) - 1 if seg.isdigit() and 1 <= int(seg) <= n else None


def _step(st: Session, seg: str) -> Session | None:
    """The session after one answer, or None when the answer is not on the menu."""
    a = dict(st.ans)
    s = st.state
    if s == "root":
        nxt = {"1": "emergency", "2": "problem", "3": "ambulance", "4": "status"}.get(seg)
        return Session(nxt, a) if nxt else None
    if s == "emergency":
        i = _pick(seg, len(EMERGENCIES))
        if i is None:
            return None
        a["emergency"] = i
        return Session("emergency_detail" if EMERGENCIES[i][2] else "area", a)
    if s == "emergency_detail":
        i = _pick(seg, len(EMERGENCIES[a["emergency"]][2] or []))
        if i is None:
            return None
        a["detail"] = i
        return Session("area", a)
    if s == "problem":
        i = _pick(seg, len(PROBLEMS))
        if i is None:
            return None
        a["problem"] = i
        return Session("who", a)
    if s == "who":
        i = _pick(seg, len(WHO))
        if i is None:
            return None
        a["who"] = i
        return Session("area", a)
    if s == "area":
        i = _pick(seg, len(_lgas()))
        if i is None:
            return None
        a["lga"] = _lgas()[i]
        return Session("submit", a)
    return None  # finished: ignore anything after


def read(text: str) -> Session:
    parts = [p.strip() for p in (text or "").split("*")] if text else []
    stack = [Session()]
    error = False
    for i, seg in enumerate(parts):
        last = i == len(parts) - 1
        if seg == "00":
            stack = [Session()]
            continue
        if seg == "0" and stack[-1].state != "root":
            stack.pop()
            continue
        nxt = _step(stack[-1], seg)
        if nxt is None:
            error = last
            continue
        stack.append(nxt)
    out = stack[-1]
    out.error = error
    return out


def screen(st: Session) -> str | None:
    """The next menu, or None when the session is finished and needs the database."""
    pre = "Please choose a number.\n" if st.error else ""
    menus = {
        "root": lambda: ROOT,
        "emergency": lambda: _menu("What is happening?", [e[0] for e in EMERGENCIES]),
        "emergency_detail": lambda: _menu("What do you see?", [d[0] for d in EMERGENCIES[st.ans["emergency"]][2] or []]),
        "problem": lambda: _menu("What is the problem?", [p[0] for p in PROBLEMS]),
        "who": lambda: _menu("Who is sick?", [w[0] for w in WHO]),
        "area": lambda: _menu("Where are you? (LGA)", _lgas()),
    }
    if st.state not in menus:
        return None
    text = menus[st.state]()
    return text.replace("CON ", "CON " + pre, 1) if pre else text


def taps_for(st: Session) -> list[dict]:
    a = st.ans
    taps: list[dict] = [{"kind": "location", "lga": a["lga"]}]
    if "emergency" in a:
        _label, code, detail = EMERGENCIES[a["emergency"]]
        taps.append({"kind": "emergency", "code": code})
        if detail and "detail" in a:
            _, sym, region = detail[a["detail"]]
            if code == "child_sick":  # danger signs are judged as for a young child: the safer reading
                taps.append({"kind": "context", "age_group": "under5"})
            taps += [{"kind": "region", "region": region}, {"kind": "symptom", "code": sym, "region": region},
                     {"kind": "severity", "value": 5}, {"kind": "onset", "value": "now"}]
    else:
        _, sym, region = PROBLEMS[a["problem"]]
        taps += [{"kind": "context", **WHO[a["who"]][1]}, {"kind": "region", "region": region},
                 {"kind": "symptom", "code": sym, "region": region}, {"kind": "severity", "value": 2},
                 {"kind": "onset", "value": "days"}]
    return taps


# ---------- finishing ----------
def normalise_phone(phone: str) -> str:
    return "+" + to_international(phone)


def _fit(text: str) -> str:
    return text if len(text) <= MAX_SCREEN else text[: MAX_SCREEN - 1] + "…"


def _short(name: str, n: int = 38) -> str:
    return name.replace(" (Demo)", "")[:n]


async def _latest_referral(db: AsyncSession, phone: str) -> Referral | None:
    return (await db.execute(
        select(Referral).join(Patient, Patient.id == Referral.patient_id)
        .where(or_(Patient.phone == phone, Patient.phone == phone.lstrip("+")))
        .order_by(Referral.created_at.desc()).limit(1)
    )).scalar_one_or_none()


async def _patient_for(db: AsyncSession, phone: str) -> Patient:
    p = (await db.execute(
        select(Patient).where(Patient.phone == phone).order_by(Patient.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if p:
        return p
    p, _key, _recovery = await create_patient(db, phone=phone)
    return p


async def _status(db: AsyncSession, phone: str) -> str:
    ref = await _latest_referral(db, phone)
    if not ref:
        return "END You have no request yet. Dial again and choose 1 or 2."
    nxt = (await db.execute(select(Referral).where(Referral.previous_referral_id == ref.id))).scalar_one_or_none()
    ref = nxt or ref
    f = await db.get(Facility, ref.facility_id)
    p = await db.get(Patient, ref.patient_id)
    assert f and p
    call = f"\nHospital: {f.phone}" if f.phone else ""
    return _fit(f"END {p.vitalis_id}: {_short(f.name)} {STATUS_WORDS.get(ReferralStatus(ref.status), ref.status)}."
                f"{call}\n{lines.call_text(f.lat, f.lng)}")


def _ambulance() -> str:
    amb = "\n".join(f"{a.name}: {a.number}" for a in lines.ambulances())  # today: Ogun State
    return _fit(f"END {amb}\nNational emergency: {lines.national().number}\n"
                "Call now. Say where you are and what happened.")


async def _submit(db: AsyncSession, phone: str, st: Session, session_id: str | None) -> str:
    lga = st.ans["lga"]
    open_ref = await _latest_referral(db, phone)
    if open_ref and open_ref.status in rsvc.OPEN_STATUSES and open_ref.created_at > utcnow() - REPEAT_WINDOW:
        return await _status(db, phone)

    patient = await _patient_for(db, phone)
    r = TriageReport(patient_id=patient.id, channel="ussd", context={}, answers={"symptoms": [], "regions": []})
    db.add(r)
    await db.flush()
    await tsvc.record_taps(db, r, taps_for(st))
    ev = await tsvc.evaluate(db, r, call_model=False)
    calls = lines.call_text(None, None, lga)
    urgent = ev.rf.fired or ev.action_level in ("go_now", "go_today")

    ref = await rsvc.create_referral(db, r, None) if urgent and ev.matches.matches else None
    await audit(db, "ussd.request", actor_type="patient", actor_id=patient.id, subject_type="triage_report",
                subject_id=r.id, details={"session": (session_id or "")[:64], "lga": lga,
                                          "referral": str(ref.id) if ref else None})
    if ref:
        f = await db.get(Facility, ref.facility_id)
        assert f
        call = f" Hospital: {f.phone}." if f.phone else ""
        go = "Go now if you can." if ev.rf.fired else "Go today."
        screen_text = (f"END Sent to {_short(f.name)} ({ref.distance_km:.0f} km). {go}{call}\n"
                       f"They will SMS you. {calls}\nID {patient.vitalis_id}")
        msg = (f"VITALIS: your request {patient.vitalis_id} was sent to {f.name}.{call} {go} "
               f"They will text you when they answer. {calls}")
    elif ev.matches.matches:
        m = ev.matches.matches[0]
        call = f" {m.phone}." if m.phone else ""
        screen_text = (f"END Not urgent. A clinic can help: {_short(m.name, 32)} ({m.distance_km:.0f} km).{call}\n"
                       f"If worse, dial again. {calls}")
        msg = (f"VITALIS: not urgent. Nearest clinic for this: {m.name}.{call} "
               f"If it gets worse, dial again or call for help. {calls}")
    else:
        screen_text = f"END No hospital near {lga} can take this on VITALIS yet. Call the ambulance now.\n{calls}"
        msg = f"VITALIS: no hospital near {lga} can take this on VITALIS yet. Call the ambulance now. {calls}"
    await sms().send(phone, msg)
    await db.commit()
    return _fit(screen_text)


async def handle(db: AsyncSession, phone: str, text: str, session_id: str | None = None) -> str:
    """One USSD screen: 'CON …' to keep going, 'END …' to finish."""
    phone = normalise_phone(phone)
    st = read(text)
    menu = screen(st)
    if menu is not None:
        return menu
    if st.state == "ambulance":
        return _ambulance()
    if st.state == "status":
        return await _status(db, phone)
    try:
        return await _submit(db, phone, st, session_id)
    except Exception:  # never leave someone on a dead screen
        log.exception("ussd submit failed")
        await db.rollback()
        return f"END Sorry, something went wrong. {lines.call_text(None, None, st.ans.get('lga'))} Call now."


def new_session_id() -> str:
    return uuid.uuid4().hex
