"""Domain exceptions and the FastAPI handlers that translate them into the
contract's error shape:

    { "error": { "code": "...", "message": "...", "details": null } }

Services/repositories raise the typed exceptions below; routers never build
error responses by hand, so the shape is enforced in exactly one place.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for domain errors that map to a specific HTTP status/code."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "error"

    def __init__(self, message: str, details: Any = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class EmployeeNotFoundError(NotFoundError):
    code = "employee_not_found"

    def __init__(self, employee_id: int) -> None:
        super().__init__(f"Employee {employee_id} does not exist")


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class EmailAlreadyExistsError(ConflictError):
    code = "email_already_exists"

    def __init__(self, email: str) -> None:
        super().__init__(f"An employee with email {email!r} already exists")


class DomainValidationError(AppError):
    """A 422 raised from a service/repository (as opposed to Pydantic's own
    request-body validation, which is handled separately below)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class SalaryEffectiveDateInvalidError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "salary_effective_date_invalid"

    def __init__(self, message: str) -> None:
        super().__init__(message)


def _error_body(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body("validation_error", "Request validation failed", details),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("internal_error", "An unexpected error occurred"),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
