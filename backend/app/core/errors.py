"""Consistent response envelope and error format.

Success: {"data": ..., "meta": {...}}   (meta optional, used for pagination)
Error:   {"error": {"code": "...", "message": "...", "details": ...}}
"""

from typing import Any, Generic, TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: PageMeta | None = None


def ok(data: Any, meta: PageMeta | None = None) -> dict:
    return {"data": data, "meta": meta}


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        self.status, self.code, self.message, self.details = status, code, message, details


def not_found(what: str = "Resource") -> AppError:
    return AppError(404, "not_found", f"{what} not found")


def forbidden(message: str = "You do not have access to this") -> AppError:
    return AppError(403, "forbidden", message)


def _body(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited"}.get(
            exc.status_code, "error"
        )
        return JSONResponse(
            _body(code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errs = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(_body("validation_error", "Invalid input", errs), status_code=422)
