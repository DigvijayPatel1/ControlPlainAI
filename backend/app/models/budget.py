"""ORM model for budget and spend tracking, per principal (or per org/team for
Phase-3 hierarchical budgets)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import PrincipalType, TimestampMixin, _utcnow


class Budget(Base, TimestampMixin):

    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    # ==========================================
    # Identity & Routing
    # ==========================================
    principal_id: Mapped[str] = mapped_column(
        String, 
        unique=True, 
        index=True, 
        nullable=False
    )
    
    principal_type: Mapped[PrincipalType] = mapped_column(
        PG_ENUM(PrincipalType, name="principal_type"), 
        nullable=False
    )

    # ==========================================
    # Financials & Thresholds
    # ==========================================
    monthly_limit_usd: Mapped[float] = mapped_column(
        Float, 
        nullable=False
    )
    
    spent_usd: Mapped[float] = mapped_column(
        Float, 
        default=0.0
    )

    # ==========================================
    # Time Boundaries
    # ==========================================
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=_utcnow
    )
    
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )

    # ==========================================
    # Telemetry & Metrics
    # ==========================================
    request_count: Mapped[int] = mapped_column(
        Integer, 
        default=0
    )
    
    blocked_count: Mapped[int] = mapped_column(
        Integer, 
        default=0
    )

    # ==========================================
    # Relationships
    # ==========================================
    parent_budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("budgets.id", ondelete="SET NULL"), 
        nullable=True
    )

    # `remote_side` must live on the many-to-one ("parent") side of a
    # self-referential relationship, not on the one-to-many ("children")
    # side — otherwise SQLAlchemy inverts which end is the collection.
    parent: Mapped["Budget | None"] = relationship(
        "Budget",
        remote_side=[id],
        back_populates="children",
        lazy="selectin",
    )

    children: Mapped[list["Budget"]] = relationship(
        "Budget",
        back_populates="parent",
        lazy="selectin",
    )