from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware, setup_logging
from app.core.ratelimit import limiter


def build_router() -> APIRouter:
    from app.api.v1 import (
        admin,
        auth,
        facilities,
        health,
        hospital,
        patients,
        referrals,
        registration,
        triage,
        worker,
    )

    api = APIRouter(prefix="/api/v1")
    for module in (health, auth, registration, patients, triage, referrals, facilities, hospital, admin, worker):
        api.include_router(module.router)
    return api


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.overdue import start_overdue_loop

    tasks = []
    if get_settings().env != "test":
        tasks.append(start_overdue_loop())
    yield
    for t in tasks:
        t.cancel()


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="VITALIS API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    install_error_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    # No CORS middleware: frontend and API are served from the same origin (nginx / Next rewrite).
    app.include_router(build_router())
    return app


app = create_app()
