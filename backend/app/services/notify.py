"""Notifications: SMS provider interface (console logger in dev). Web Push is wired in Phase 4b."""

import logging
from typing import Protocol

from app.core.config import get_settings

log = logging.getLogger("vitalis.notify")


class SmsProvider(Protocol):
    async def send(self, phone: str, message: str) -> None: ...


def mask_phone(phone: str) -> str:
    return phone[:4] + "***" + phone[-2:] if len(phone) > 6 else "***"


class ConsoleSms:
    """Dev provider: logs a masked number and the (non-clinical) message."""

    sent: list[tuple[str, str]] = []

    async def send(self, phone: str, message: str) -> None:
        ConsoleSms.sent.append((phone, message))
        log.info("sms", extra={"fields": {"to": mask_phone(phone), "sms": message}})


def sms() -> SmsProvider:
    provider = get_settings().sms_provider
    # Africa's Talking / Termii adapters plug in here.
    if provider == "console":
        return ConsoleSms()
    raise RuntimeError(f"Unknown SMS provider {provider}")
