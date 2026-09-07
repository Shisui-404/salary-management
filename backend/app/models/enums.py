"""Domain enums, shared between SQLAlchemy models and Pydantic schemas.

Single source of truth for the allowed values in the API contract so the
database CHECK-style constraint (via SQLAlchemy `Enum`) and the request/
response validation never drift apart.
"""

from enum import StrEnum


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"
    NON_BINARY = "non_binary"
    UNDISCLOSED = "undisclosed"


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


class ChangeReason(StrEnum):
    INITIAL = "initial"
    ANNUAL_REVIEW = "annual_review"
    PROMOTION = "promotion"
    MARKET_ADJUSTMENT = "market_adjustment"
    ROLE_CHANGE = "role_change"
    CORRECTION = "correction"


class BandPosition(StrEnum):
    BELOW = "below"
    WITHIN = "within"
    ABOVE = "above"
    UNBANDED = "unbanded"
