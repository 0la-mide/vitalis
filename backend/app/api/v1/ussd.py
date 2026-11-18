"""USSD for any phone, and the numbers to call.

POST /ussd is the gateway callback (Africa's Talking format: form fields sessionId, serviceCode, phoneNumber, text;
the reply is plain text starting with CON or END). The gateway is set up to call /api/v1/ussd?key=USSD_SECRET.

The website's USSD simulator uses /demo/ussd with demo phone numbers (0000 000 0xxx) and reads the texts those
numbers would have received from /demo/sms. Demo numbers never reach a real SMS gateway.
"""

import hmac
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import guard
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError, Envelope, ok
from app.core.ratelimit import limiter
from app.schemas.triage import Line
from app.services import lines
from app.services import ussd as svc
from app.services.notify import demo_inbox, is_demo_phone

router = APIRouter(tags=["ussd"])


class LinesOut(BaseModel):
    national: Line
    ambulances: list[Line]
    ussd_code: str


@router.get("/lines", response_model=Envelope[LinesOut])
async def numbers():
    """Public: the national emergency line, the state ambulances VITALIS knows, and the USSD code."""
    return ok(LinesOut(national=lines.national(), ambulances=lines.ambulances(), ussd_code=get_settings().ussd_code))


@router.post("/ussd", response_class=PlainTextResponse)
@limiter.limit("600/minute")  # every caller arrives from the gateway's few IPs; the secret is the real gate
async def ussd_callback(request: Request, key: str = "", db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if s.ussd_secret:
        if not hmac.compare_digest(key, s.ussd_secret):
            raise AppError(403, "forbidden", "Forbidden")
    elif s.is_prod:
        raise AppError(404, "not_found", "Not found")
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode("utf-8", "replace")).items()}
    phone = form.get("phoneNumber", "")
    if not phone:
        return PlainTextResponse("END Sorry, we could not read your number.")
    reply = await svc.handle(db, phone, form.get("text", ""), form.get("sessionId"))
    return PlainTextResponse(reply)


# ---------- the simulator on the website (demo numbers only) ----------
class DemoUssdIn(BaseModel):
    phone: str = Field(max_length=20)
    text: str = Field(default="", max_length=120, pattern=r"^[0-9*#]*$")


class DemoUssdOut(BaseModel):
    reply: str
    done: bool


class DemoSms(BaseModel):
    at: str
    text: str


def _demo_phone(phone: str) -> None:
    if not get_settings().demo_logins_enabled:
        raise AppError(404, "not_found", "Not found")
    if not is_demo_phone(phone):
        raise AppError(422, "validation_error", "The simulator only works with demo numbers (0000 000 0xxx)")


@router.post("/demo/ussd", response_model=Envelope[DemoUssdOut])
@limiter.limit("300/minute")
async def demo_ussd(request: Request, body: DemoUssdIn, db: AsyncSession = Depends(get_db)):
    _demo_phone(body.phone)
    # Finishing a session alerts a hospital: cap those per network so nobody can flood the demo hospitals.
    net = get_remote_address(request)
    if svc.read(body.text).state == "submit":
        if guard.enabled() and guard.ussd_requests.blocked(net):
            raise AppError(429, "too_many_requests", "Too many USSD requests from this network. Try again later.")
        guard.ussd_requests.hit(net)
    reply = await svc.handle(db, body.phone, body.text, "simulator")
    return ok(DemoUssdOut(reply=reply[4:], done=reply.startswith("END")))


@router.get("/demo/sms", response_model=Envelope[list[DemoSms]])
@limiter.limit("300/minute")  # the simulator polls every 3 s; a room full of people shares one IP
async def demo_sms(request: Request, phone: str):
    _demo_phone(phone)
    return ok([DemoSms(**m) for m in reversed(demo_inbox(phone))])
