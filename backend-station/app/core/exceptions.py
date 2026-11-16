"""Application exceptions and their public error representation."""

from typing import Any


class AppError(Exception):
    """Base exception for expected application failures."""

    status_code = 400
    code = "APPLICATION_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
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


class IdempotencyConflictError(AppError):
    status_code = 409
    code = "IDEMPOTENCY_KEY_REUSED"


class VoucherAlreadyExistsError(AppError):
    status_code = 409
    code = "VOUCHER_ALREADY_EXISTS"


class InsufficientOrderBalanceError(AppError):
    status_code = 409
    code = "INSUFFICIENT_ORDER_BALANCE"


class InsufficientVoucherBalanceError(AppError):
    status_code = 409
    code = "INSUFFICIENT_VOUCHER_BALANCE"


class InvalidFuelLineError(AppError):
    status_code = 422
    code = "INVALID_FUEL_LINE"


class AttendanceAlreadyVerifiedError(AppError):
    status_code = 409
    code = "ATTENDANCE_ALREADY_VERIFIED"


class VoucherHasAttendancesError(AppError):
    status_code = 409
    code = "VOUCHER_HAS_ATTENDANCES"


class InvalidVerificationError(AppError):
    status_code = 422
    code = "INVALID_VERIFICATION"
