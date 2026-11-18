"""Small in-process counters for abuse that per-IP rate limits miss.

- Login lockout per account: password guessing spread over many IPs still hits one account's counter.
- A per-network budget for actions that alert hospitals (USSD requests from the simulator).

One backend process (see deploy/backend.Dockerfile), so memory is enough; counters reset on restart.
"""

import time
from collections import deque

from app.core.config import get_settings
from app.core.errors import AppError


class Window:
    """At most `limit` events per key in the last `seconds`."""

    def __init__(self, limit: int, seconds: int, max_keys: int = 50_000):
        self.limit, self.seconds, self.max_keys = limit, seconds, max_keys
        self._hits: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        q = self._hits.get(key)
        if q is None:
            if len(self._hits) >= self.max_keys:  # never grow without bound under a flood
                self._hits.clear()
            q = self._hits[key] = deque()
        while q and q[0] <= now - self.seconds:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        return len(self._recent(key, time.monotonic())) >= self.limit

    def hit(self, key: str) -> None:
        self._recent(key, time.monotonic()).append(time.monotonic())

    def clear(self, key: str) -> None:
        self._hits.pop(key, None)

    def retry_after(self, key: str) -> int:
        q = self._recent(key, time.monotonic())
        return max(1, int(q[0] + self.seconds - time.monotonic())) if q else 0


def enabled() -> bool:
    return get_settings().rate_limit_enabled


# Every API request, per IP: a safety net under each route's own limit (see DefaultLimitMiddleware).
api_requests = Window(limit=1200, seconds=60)
# 8 wrong passwords for one account in 15 minutes locks that account for the rest of the window.
login_failures = Window(limit=8, seconds=15 * 60)
# USSD requests that alert a hospital, per network (the simulator): a venue's shared Wi-Fi still has room.
ussd_requests = Window(limit=60, seconds=3600)


def check_login(email: str) -> None:
    key = email.strip().lower()
    if enabled() and login_failures.blocked(key):
        mins = max(1, login_failures.retry_after(key) // 60)
        raise AppError(429, "too_many_attempts", f"Too many wrong passwords. Try again in {mins} min.")
