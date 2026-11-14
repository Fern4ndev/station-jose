"""Application exceptions and their public error representation."""


class AppError(Exception):
    """Base exception for expected application failures."""

    status_code = 400
    code = "APPLICATION_ERROR"

    def __init__(self, message: str, *, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ResourceNotFoundError(AppError):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "DATABASE_UNAVAILABLE"


class AuthenticationRequiredError(AppError):
    status_code = 401
    code = "AUTHENTICATION_REQUIRED"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"
