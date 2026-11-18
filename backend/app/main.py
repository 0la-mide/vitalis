from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.middleware import (
    DefaultLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    setup_logging,
)
from app.core.ratelimit import limiter


def build_router() -> APIRouter:
    from app.api.v1 import (
        admin,
        auth,
        clinical,
        console,
        demo,
        encounters,
        facilities,
        health,
        hospital,
        me,
        network,
        offline,
        patients,
        push,
        referrals,
        registration,
        triage,
        ussd,
        worker,
    )

    api = APIRouter(prefix="/api/v1")
    for module in (health, auth, registration, patients, triage, referrals, facilities, hospital, encounters, clinical, admin, worker, me, network, demo, push, offline, ussd, console):
        api.include_router(module.router)
    return api


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.overdue import start_overdue_loop

    tasks = []
    if get_settings().env != "test":
        tasks.append(start_overdue_loop())
        # Load the team's models in the background so the first doctor request is fast.
        import asyncio

        from app.engines.ncs_models.adapter import warm_up

        tasks.append(asyncio.create_task(asyncio.to_thread(warm_up)))
    yield
    for t in tasks:
        t.cancel()


def _too_many(request, exc):
    """Same error shape as every other API error, so the app shows a calm message."""
    return JSONResponse(
        {"error": {"code": "rate_limited", "message": "Too many requests. Please wait a moment and try again.",
                   "details": None}},
        status_code=429, headers={"Retry-After": "60"},
    )


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="VITALIS API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/api/docs",
        openapi_url=None if settings.is_prod else "/api/openapi.json",  # don't publish a map of the API in prod
        redoc_url=None,
    )
    if settings.is_prod and (settings.jwt_secret.startswith("dev-only") or len(settings.jwt_secret) < 32):
        raise RuntimeError("Set JWT_SECRET in .env to a long random value (deploy.sh does this for you).")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _too_many)
    # Safety net: every API route, per IP, on top of each route's own @limiter.limit.
    app.add_middleware(DefaultLimitMiddleware)
    install_error_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    # No CORS middleware: frontend and API are served from the same origin (nginx / Next rewrite).
    app.include_router(build_router())
    return app


app = create_app()
