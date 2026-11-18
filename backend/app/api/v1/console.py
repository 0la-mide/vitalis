"""Network admin console: everything about the network at a glance. Network admin only.

People are counted, not listed: patients appear only as numbers and anonymous devices (no names, no VITALIS IDs),
because a patient's identity belongs to the hospitals she consents to. Staff and chemists are listed by name: they
are accounts the network admin approves.
"""

import csv
import io
import re
import statistics
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Date, case, cast, distinct, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin import network_admin
from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.errors import Envelope, PageMeta, ok
from app.models import (
    AIDraft,
    AuditEvent,
    Facility,
    ModelPrediction,
    Patient,
    PushSubscription,
    Referral,
    TriageReport,
    User,
    WorkerProfile,
)
from app.models.enums import ReferralStatus

router = APIRouter(prefix="/admin/console", tags=["admin"])
LAGOS = ZoneInfo("Africa/Lagos")


def _day(col):
    return cast(func.timezone(literal_column("'Africa/Lagos'"), col), Date)  # days as Nigerians live them (WAT)


def _today() -> date:
    return utcnow().astimezone(LAGOS).date()


def _channel():
    return case((TriageReport.channel == "ussd", literal_column("'ussd'")),
                (TriageReport.worker_id.is_not(None), literal_column("'chemist'")), else_=literal_column("'app'"))


# ---------- overview ----------
class DayRow(BaseModel):
    date: date
    app: int = 0
    chemist: int = 0
    ussd: int = 0
    emergencies: int = 0
    referrals: int = 0
    new_patients: int = 0
    new_accounts: int = 0
    sign_ins: int = 0


class Overview(BaseModel):
    days: int
    patients: int
    patients_active_7d: int
    patients_active_24h: int
    patients_by_chemist: int
    patients_by_ussd: int
    accounts_by_role: dict[str, int]
    accounts_by_status: dict[str, int]
    facilities_by_status: dict[str, int]
    devices_with_alerts: int
    requests_by_channel: dict[str, int]
    funnel: dict[str, int]
    sign_ins_24h: int
    series: list[DayRow]


@router.get("/overview", response_model=Envelope[Overview])
async def overview(days: int = Query(30, ge=7, le=90), _: User = Depends(network_admin),
                   db: AsyncSession = Depends(get_db)):
    now = utcnow()
    since = now - timedelta(days=days)

    async def scalar(q) -> int:
        return int((await db.execute(q)).scalar_one() or 0)

    async def grouped(col, model) -> dict[str, int]:
        return {str(k): int(v) for k, v in (await db.execute(select(col, func.count()).select_from(model).group_by(col))).all()}

    series: dict[date, DayRow] = {}
    start = _today() - timedelta(days=days - 1)
    for i in range(days):
        d = start + timedelta(days=i)
        series[d] = DayRow(date=d)

    def put(rows, field):
        for d, n in rows:
            if d in series:
                setattr(series[d], field, getattr(series[d], field) + int(n))

    ch = _channel()
    for d, c, n in (await db.execute(
        select(_day(TriageReport.created_at), ch, func.count()).where(TriageReport.created_at >= since)
        .group_by(_day(TriageReport.created_at), ch)
    )).all():
        if d in series:
            setattr(series[d], str(c), int(n))
    put((await db.execute(select(_day(TriageReport.created_at), func.count()).where(
        TriageReport.created_at >= since, TriageReport.red_flag).group_by(_day(TriageReport.created_at)))).all(), "emergencies")
    put((await db.execute(select(_day(Referral.created_at), func.count()).where(Referral.created_at >= since)
                          .group_by(_day(Referral.created_at)))).all(), "referrals")
    put((await db.execute(select(_day(Patient.created_at), func.count()).where(Patient.created_at >= since)
                          .group_by(_day(Patient.created_at)))).all(), "new_patients")
    put((await db.execute(select(_day(User.created_at), func.count()).where(User.created_at >= since)
                          .group_by(_day(User.created_at)))).all(), "new_accounts")
    put((await db.execute(select(_day(AuditEvent.created_at), func.count()).where(
        AuditEvent.created_at >= since, AuditEvent.action == "auth.login").group_by(_day(AuditEvent.created_at)))).all(),
        "sign_ins")

    accepted_ever = or_(Referral.accepted_at.is_not(None), Referral.arrived_at.is_not(None))
    return ok(Overview(
        days=days,
        patients=await scalar(select(func.count()).select_from(Patient)),
        patients_active_7d=await scalar(select(func.count()).select_from(Patient).where(Patient.last_seen_at >= now - timedelta(days=7))),
        patients_active_24h=await scalar(select(func.count()).select_from(Patient).where(Patient.last_seen_at >= now - timedelta(hours=24))),
        patients_by_chemist=await scalar(select(func.count()).select_from(Patient).where(Patient.created_by_worker_id.is_not(None))),
        patients_by_ussd=await scalar(select(func.count(distinct(TriageReport.patient_id))).where(TriageReport.channel == "ussd")),
        accounts_by_role=await grouped(User.role, User),
        accounts_by_status=await grouped(User.status, User),
        facilities_by_status=await grouped(Facility.status, Facility),
        devices_with_alerts=await scalar(select(func.count()).select_from(PushSubscription)),
        requests_by_channel={str(k): int(v) for k, v in (await db.execute(
            select(ch, func.count()).select_from(TriageReport).group_by(ch))).all()},
        funnel={
            "requests": await scalar(select(func.count()).select_from(TriageReport)),
            "referred": await scalar(select(func.count(distinct(Referral.report_id)))),
            "accepted": await scalar(select(func.count()).select_from(Referral).where(accepted_ever)),
            "arrived": await scalar(select(func.count()).select_from(Referral).where(Referral.arrived_at.is_not(None))),
            "declined": await scalar(select(func.count()).select_from(Referral).where(Referral.status == ReferralStatus.declined)),
        },
        sign_ins_24h=await scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action == "auth.login", AuditEvent.created_at >= now - timedelta(hours=24))),
        series=list(series.values()),
    ))


# ---------- accounts ----------
class AccountRow(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    role: str
    status: str
    facility: str | None
    business: str | None
    created_at: datetime
    last_login_at: datetime | None
    sign_ins_30d: int


@router.get("/accounts", response_model=Envelope[list[AccountRow]])
async def accounts(
    role: str | None = Query(None, max_length=32), status: str | None = Query(None, max_length=16),
    q: str | None = Query(None, max_length=80), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    _: User = Depends(network_admin), db: AsyncSession = Depends(get_db),
):
    query = select(User, Facility.name, WorkerProfile.business_name).outerjoin(Facility, Facility.id == User.facility_id) \
        .outerjoin(WorkerProfile, WorkerProfile.user_id == User.id)
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(User.full_name.ilike(like), User.email.ilike(like), Facility.name.ilike(like),
                                WorkerProfile.business_name.ilike(like)))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (await db.execute(query.order_by(User.created_at.desc()).limit(limit).offset(offset))).all()
    ids = [u.id for u, _f, _b in rows]
    logins = dict((await db.execute(
        select(AuditEvent.actor_id, func.count()).where(
            AuditEvent.action == "auth.login", AuditEvent.actor_id.in_(ids),
            AuditEvent.created_at >= utcnow() - timedelta(days=30)).group_by(AuditEvent.actor_id)
    )).all()) if ids else {}
    return ok([AccountRow(id=u.id, full_name=u.full_name, email=u.email, phone=u.phone, role=u.role, status=u.status,
                          facility=f, business=b, created_at=u.created_at, last_login_at=u.last_login_at,
                          sign_ins_30d=int(logins.get(u.id, 0))) for u, f, b in rows],
              PageMeta(total=total, limit=limit, offset=offset))


# ---------- devices ----------
def browser_of(endpoint: str, ua: str | None) -> str:
    u = ua or ""
    if "Edg/" in u:
        b = "Edge"
    elif "SamsungBrowser" in u:
        b = "Samsung Internet"
    elif "Firefox" in u or "mozilla.com" in endpoint:
        b = "Firefox"
    elif "Chrome" in u or "googleapis.com" in endpoint:
        b = "Chrome"
    elif "Safari" in u or "push.apple.com" in endpoint:
        b = "Safari"
    else:
        b = "Other"
    return b


def os_of(ua: str | None) -> str:
    u = ua or ""
    for pat, name in ((r"iPhone|iPad|iOS", "iPhone / iPad"), (r"Android", "Android"), (r"Windows", "Windows"),
                      (r"Mac OS X|Macintosh", "Mac"), (r"Linux", "Linux")):
        if re.search(pat, u):
            return name
    return "Unknown"


class DeviceRow(BaseModel):
    owner: str  # "Patient phone" or the staff member's role and name
    browser: str
    os: str
    since: datetime


class Devices(BaseModel):
    phones_with_card: int
    phones_active_24h: int
    phones_active_7d: int
    phones_active_30d: int
    alerts_total: int
    alerts_patients: int
    alerts_staff: int
    by_browser: dict[str, int]
    by_os: dict[str, int]
    recent: list[DeviceRow]


@router.get("/devices", response_model=Envelope[Devices])
async def devices(_: User = Depends(network_admin), db: AsyncSession = Depends(get_db)):
    now = utcnow()

    async def active(delta: timedelta) -> int:
        return int((await db.execute(select(func.count()).select_from(Patient).where(Patient.last_seen_at >= now - delta))).scalar_one())

    subs = (await db.execute(select(PushSubscription, User).outerjoin(User, User.id == PushSubscription.user_id)
                             .order_by(PushSubscription.created_at.desc()))).all()
    by_browser: dict[str, int] = {}
    by_os: dict[str, int] = {}
    recent = []
    for s, u in subs:
        b, o = browser_of(s.endpoint, s.user_agent), os_of(s.user_agent)
        by_browser[b] = by_browser.get(b, 0) + 1
        by_os[o] = by_os.get(o, 0) + 1
        if len(recent) < 100:
            owner = f"{u.role.replace('_', ' ')} · {u.full_name}" if u else "Patient phone"
            recent.append(DeviceRow(owner=owner, browser=b, os=o, since=s.created_at))
    return ok(Devices(
        phones_with_card=int((await db.execute(select(func.count()).select_from(Patient))).scalar_one()),
        phones_active_24h=await active(timedelta(hours=24)), phones_active_7d=await active(timedelta(days=7)),
        phones_active_30d=await active(timedelta(days=30)),
        alerts_total=len(subs), alerts_patients=sum(1 for s, _u in subs if s.patient_id),
        alerts_staff=sum(1 for s, _u in subs if s.user_id), by_browser=by_browser, by_os=by_os, recent=recent,
    ))


# ---------- models ----------
class ModelDay(BaseModel):
    date: date
    ok: int = 0
    failed: int = 0


class VersionRow(BaseModel):
    version: str
    calls: int
    ok_rate: float


class Models(BaseModel):
    service_up: bool
    service_ms: int | None
    triage_calls: int
    triage_calls_24h: int
    triage_ok_rate: float | None
    triage_avg_ms: float | None
    triage_p95_ms: float | None
    triage_versions: list[VersionRow]
    triage_last_error: str | None
    triage_last_error_at: datetime | None
    series: list[ModelDay]
    risk_models_enabled: bool
    ai_drafts: int
    ai_by_provider: dict[str, int]
    ai_by_action: dict[str, int]
    ai_model_versions: list[str]


@router.get("/models", response_model=Envelope[Models])
async def models(days: int = Query(14, ge=7, le=90), _: User = Depends(network_admin), db: AsyncSession = Depends(get_db)):
    s = get_settings()
    now = utcnow()
    up, ms = False, None
    try:
        t0 = datetime.now()
        async with httpx.AsyncClient(timeout=2.0) as c:
            up = (await c.get(f"{s.model_url.rstrip('/')}/health")).status_code == 200
        ms = int((datetime.now() - t0).total_seconds() * 1000)
    except httpx.HTTPError:
        up = False

    total = int((await db.execute(select(func.count()).select_from(ModelPrediction))).scalar_one())
    lat = [r for (r,) in (await db.execute(select(ModelPrediction.latency_ms).where(
        ModelPrediction.created_at >= now - timedelta(days=days), ModelPrediction.ok).limit(20000))).all()]
    oks = int((await db.execute(select(func.count()).select_from(ModelPrediction).where(ModelPrediction.ok))).scalar_one())
    versions = [VersionRow(version=v, calls=int(n), ok_rate=round(float(k or 0) / n, 3) if n else 0.0)
                for v, n, k in (await db.execute(select(
                    ModelPrediction.model_version, func.count(),
                    func.sum(case((ModelPrediction.ok, 1), else_=0))).group_by(ModelPrediction.model_version))).all()]
    last_err = (await db.execute(select(ModelPrediction.error, ModelPrediction.created_at).where(
        ModelPrediction.ok.is_(False)).order_by(ModelPrediction.created_at.desc()).limit(1))).first()
    series: dict[date, ModelDay] = {}
    start = _today() - timedelta(days=days - 1)
    for i in range(days):
        series[start + timedelta(days=i)] = ModelDay(date=start + timedelta(days=i))
    for d, okk, n in (await db.execute(select(_day(ModelPrediction.created_at), ModelPrediction.ok, func.count()).where(
            ModelPrediction.created_at >= now - timedelta(days=days)).group_by(_day(ModelPrediction.created_at), ModelPrediction.ok))).all():
        if d in series:
            if okk:
                series[d].ok += int(n)
            else:
                series[d].failed += int(n)
    drafts = (await db.execute(select(AIDraft.narrative_provider, AIDraft.action, AIDraft.model_versions))).all()
    prov: dict[str, int] = {}
    act: dict[str, int] = {}
    mv: set[str] = set()
    for p, a, v in drafts:
        prov[p] = prov.get(p, 0) + 1
        act[a] = act.get(a, 0) + 1
        mv.update(str(x) for x in (v or []))
    return ok(Models(
        service_up=up, service_ms=ms, triage_calls=total,
        triage_calls_24h=int((await db.execute(select(func.count()).select_from(ModelPrediction).where(
            ModelPrediction.created_at >= now - timedelta(hours=24)))).scalar_one()),
        triage_ok_rate=round(oks / total, 3) if total else None,
        triage_avg_ms=round(statistics.fmean(lat), 1) if lat else None,
        triage_p95_ms=float(sorted(lat)[int(0.95 * (len(lat) - 1))]) if lat else None,
        triage_versions=versions, triage_last_error=last_err[0] if last_err else None,
        triage_last_error_at=last_err[1] if last_err else None, series=list(series.values()),
        risk_models_enabled=s.enable_ncs_models, ai_drafts=len(drafts), ai_by_provider=prov, ai_by_action=act,
        ai_model_versions=sorted(mv),
    ))


# ---------- audit export ----------
@router.get("/audit.csv")
async def audit_csv(
    action: str | None = Query(None, max_length=64), actor_type: str | None = Query(None, max_length=16),
    since: datetime | None = None, until: datetime | None = None,
    admin: User = Depends(network_admin), db: AsyncSession = Depends(get_db),
):
    """Up to 10,000 events as CSV. Patients appear only as 'patient' (never named). The export itself is audited."""
    q = select(AuditEvent, User.full_name, User.email, Facility.name).outerjoin(
        User, (User.id == AuditEvent.actor_id) & (AuditEvent.actor_type == "user")).outerjoin(
        Facility, Facility.id == AuditEvent.facility_id)
    if action:
        q = q.where(AuditEvent.action.startswith(action))
    if actor_type:
        q = q.where(AuditEvent.actor_type == actor_type)
    if since:
        q = q.where(AuditEvent.created_at >= since)
    if until:
        q = q.where(AuditEvent.created_at <= until)
    rows = (await db.execute(q.order_by(AuditEvent.created_at.desc()).limit(10000))).all()
    await audit(db, "audit.export", actor_id=admin.id, details={"rows": len(rows), "action": action, "actor_type": actor_type})
    await db.commit()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time_utc", "action", "actor_type", "actor_name", "actor_email", "facility", "subject_type",
                "subject_id", "details", "request_id"])
    for e, name, email, fac in rows:
        w.writerow([e.created_at.isoformat(), e.action, e.actor_type, name or "", email or "", fac or "",
                    e.subject_type or "", str(e.subject_id or ""), e.details or "", e.request_id or ""])
    stamp = utcnow().strftime("%Y%m%d-%H%M")
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="vitalis-audit-{stamp}.csv"'})
