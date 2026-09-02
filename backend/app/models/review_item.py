"""ORM model for items awaiting human-in-the-loop review."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import ReviewAction, TimestampMixin

if TYPE_CHECKING:
    from app.models.request_log import RequestLog


class ReviewItem(Base, TimestampMixin):

    __tablename__ = "review_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    # ==========================================
    # Identity & Routing
    # ==========================================
    request_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("request_logs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # ==========================================
    # Payload & Context
    # ==========================================
    prompt: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    
    proposed_response: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )

    # ==========================================
    # Guardrail & Safety Metrics
    # ==========================================
    flagged_reason: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    
    risk_score: Mapped[float] = mapped_column(
        Float, 
        nullable=False
    )

    # ==========================================
    # Resolution & State
    # ==========================================
    resolved: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        index=True
    )
    
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # admin principal id
    resolved_by: Mapped[str | None] = mapped_column(
        String, 
        nullable=True
    )
    
    action_taken: Mapped[ReviewAction | None] = mapped_column(
        PG_ENUM(ReviewAction, name="review_action"), 
        nullable=True
    )
    
    final_response: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True
    )

    # ==========================================
    # Relationships
    # ==========================================
    request_log: Mapped[RequestLog] = relationship(
        back_populates="review_item",
        lazy="selectin"
    )