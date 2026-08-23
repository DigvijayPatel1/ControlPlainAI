import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class Verdict(str, enum.Enum):
    PASS = "pass"
    MASK = "mask"
    BLOCK = "block"
    REVIEW = "review"


class EnforcementAction(str, enum.Enum):
    ALLOW = "allow"
    MASK = "mask"
    BLOCK = "block"
    MONITOR = "monitor"


class SecurityPolicy(str, enum.Enum):
    BLOCK = "block"
    MASK = "mask"
    MONITOR = "monitor"


class PrincipalType(str, enum.Enum):
    API_KEY = "api_key"
    EXTENSION = "extension"          # Entra-enrolled browser extension


class ChatbotCategory(str, enum.Enum):
    CUSTOMER_SUPPORT = "customer_support"
    INTERNAL_EMPLOYEE = "internal_employee"
    REGULATED_DECISION = "regulated_decision"


class ReviewAction(str, enum.Enum):
    APPROVE = "approve"
    EDIT = "edit"
    OVERRIDE = "override"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds created_at / updated_at columns to any model that inherits it."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )