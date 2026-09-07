"""Shared response DTOs: the pagination envelope and the `Money` object.

Every list endpoint returns the same `{items, total, limit, offset}` shape
(the contract's pagination envelope); every monetary field on every response
uses `Money` (amount as a decimal *string*, never a JSON number).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Money(BaseModel):
    amount: str
    currency: str


class Page[T](BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Documents the contract's error shape for OpenAPI; the actual response
    is built by `core/errors.py` exception handlers, not returned directly
    by a route, so this exists for schema/documentation purposes."""

    error: ErrorBody
