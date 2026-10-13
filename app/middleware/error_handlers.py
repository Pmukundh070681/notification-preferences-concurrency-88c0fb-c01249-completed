"""One JSON envelope for every refusal:
{"error": {"code", "message", "hint", "details"}}"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import AppError


def _envelope(status, code, message, hint=None, details=None, headers=None):
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={"error": {"code": code, "message": message, "hint": hint, "details": details or {}}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _envelope(exc.status_code, exc.code, exc.message, exc.hint, exc.details, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        problems = [{"field": ".".join(str(p) for p in e["loc"]), "problem": e["msg"]} for e in exc.errors()]
        return _envelope(422, "VALIDATION_ERROR", "Request is invalid.", details={"problems": problems})
