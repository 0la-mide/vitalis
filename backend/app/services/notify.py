"""Notifications: SMS to families and frontline workers.

SMS_PROVIDER picks the gateway: console (dev, logs only), termii, or bulksmsnigeria. Both real gateways reach
Nigerian numbers and give free sign-up credit. A failed SMS is logged and never breaks the request that sent it.
"""

import asyncio
import logging
from typing import Protocol

import httpx

from app.core.config import get_settings

log = logging.getLogger("vitalis.notify")


class SmsProvider(Protocol):
    async def send(self, phone: str, message: str) -> None: ...


def mask_phone(phone: str) -> str:
    return phone[:4] + "***" + phone[-2:] if len(phone) > 6 else "***"


def to_international(phone: str) -> str:
    """'0803 123 4567' / '+2348031234567' / '2348031234567' -> '2348031234567' (Nigeria default)."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0") and len(digits) == 11:
        return "234" + digits[1:]
    return digits


class ConsoleSms:
    """Dev provider: logs a masked number and the (non-clinical) message."""

    sent: list[tuple[str, str]] = []

    async def send(self, phone: str, message: str) -> None:
        ConsoleSms.sent.append((phone, message))
        log.info("sms", extra={"fields": {"to": mask_phone(phone), "sms": message}})


class _HttpSms:
    name = "http"

    def request(self, to: str, message: str) -> tuple[str, dict, dict]:
        raise NotImplementedError

    _pending: set[asyncio.Task] = set()

    async def send(self, phone: str, message: str) -> None:
        # Deliver in the background: a slow gateway must never hold up a hospital's tap.
        task = asyncio.create_task(self._deliver(phone, message))
        _HttpSms._pending.add(task)
        task.add_done_callback(_HttpSms._pending.discard)

    async def _deliver(self, phone: str, message: str) -> None:
        to = to_international(phone)
        url, headers, body = self.request(to, message)
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.post(url, json=body, headers=headers)
            ok = r.status_code < 300
            log.info("sms", extra={"fields": {"provider": self.name, "to": mask_phone(to), "status": r.status_code,
                                              "ok": ok, "reply": r.text[:200] if not ok else None}})
        except httpx.HTTPError as e:
            log.warning("sms failed", extra={"fields": {"provider": self.name, "to": mask_phone(to), "error": str(e)}})


class TermiiSms(_HttpSms):
    """https://developers.termii.com/messaging-api  (POST {base}/api/sms/send)."""

    name = "termii"

    def request(self, to: str, message: str) -> tuple[str, dict, dict]:
        s = get_settings()
        return (
            f"{s.termii_base_url.rstrip('/')}/api/sms/send",
            {"Accept": "application/json"},
            {"api_key": s.termii_api_key, "to": to, "from": s.sms_sender_id, "sms": message,
             "type": "plain", "channel": s.termii_channel},
        )


class BulkSmsNigeria(_HttpSms):
    """https://www.bulksmsnigeria.com/api  (POST /api/v2/sms, Bearer token)."""

    name = "bulksmsnigeria"

    def request(self, to: str, message: str) -> tuple[str, dict, dict]:
        s = get_settings()
        return (
            "https://www.bulksmsnigeria.com/api/v2/sms",
            {"Authorization": f"Bearer {s.bulksmsnigeria_api_token}", "Accept": "application/json"},
            {"from": s.sms_sender_id, "to": to, "body": message, "gateway": s.bulksmsnigeria_gateway},
        )


def sms() -> SmsProvider:
    provider = get_settings().sms_provider
    if provider == "termii":
        return TermiiSms()
    if provider == "bulksmsnigeria":
        return BulkSmsNigeria()
    if provider == "console":
        return ConsoleSms()
    raise RuntimeError(f"Unknown SMS provider {provider}")
