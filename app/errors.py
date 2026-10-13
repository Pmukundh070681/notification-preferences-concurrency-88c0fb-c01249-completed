"""Domain errors. Framework-free; rendered into JSON by app/middleware/error_handlers.py."""


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, hint: str | None = None,
                 details: dict | None = None, headers: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.hint = hint
        self.details = details or {}
        self.headers = headers or {}


class AuthenticationRequired(AppError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"

    def __init__(self, message: str, **kw):
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"}, **kw)


class Forbidden(AppError):
    """The caller is not allowed to do this (who they are / which tenant)."""
    status_code = 403
    code = "FORBIDDEN"


class BadRequest(AppError):
    status_code = 400
    code = "BAD_REQUEST"


class VersionRequired(AppError):
    status_code = 428
    code = "VERSION_REQUIRED"


class VersionConflict(AppError):
    """The caller IS allowed, but the record changed since they read it."""
    status_code = 412
    code = "VERSION_CONFLICT"
