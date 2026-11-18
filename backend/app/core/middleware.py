import contextvars
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload)


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


log = logging.getLogger("vitalis.http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID and logs method/path/status/duration. Never logs bodies."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        log.info(
            "request",
            extra={
                "fields": {
                    "request_id": rid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - start) * 1000, 1),
                }
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if request.url.scheme == "https":
            h.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response


class DefaultLimitMiddleware(BaseHTTPMiddleware):
    """At most 1200 API requests a minute from one IP, for every route.

    Generous on purpose: a hospital or a venue's Wi-Fi puts many people behind one IP. Routes that create things
    or check secrets have their own, tighter limits. Health checks and live streams are not counted.
    """

    SKIP = ("/api/v1/health",)

    async def dispatch(self, request: Request, call_next):
        from app.core import guard

        path = request.url.path
        w = guard.api_requests
        if guard.enabled() and path.startswith("/api/") \
                and path not in self.SKIP and not path.endswith("/stream"):
            ip = request.client.host if request.client else "unknown"
            if w.blocked(ip):
                return JSONResponse(
                    {"error": {"code": "rate_limited", "message": "Too many requests. Please wait a moment and try again.",
                               "details": None}},
                    status_code=429, headers={"Retry-After": str(w.retry_after(ip))},
                )
            w.hit(ip)
        return await call_next(request)
