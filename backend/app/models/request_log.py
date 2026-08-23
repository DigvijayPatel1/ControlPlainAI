"""ORM model for a single guardrailed request/response pair."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import ChatbotCategory, PrincipalType, TimestampMixin, Verdict

if TYPE_CHECKING:
    from app.models.review_item import ReviewItem


class RequestLog(Base, TimestampMixin):
    """
    One row per proxied call. `created_at` from TimestampMixin doubles as
    the log timestamp.
    """

    __tablename__ = "request_logs"

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
        index=True, 
        nullable=False
    )
    
    principal_type: Mapped[PrincipalType] = mapped_column(
        PG_ENUM(PrincipalType, name="principal_type"), 
        nullable=False
    )
    
    chatbot_category: Mapped[ChatbotCategory | None] = mapped_column(
        PG_ENUM(ChatbotCategory, name="chatbot_category"), 
        nullable=True
    )

    # ==========================================
    # Payload & Context
    # ==========================================
    prompt: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    
    context: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True
    )
    
    # The output from the LLM before any guardrail interventions
    response_raw: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    
    # The final output delivered to the user after potential corrections
    response_final: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )

    # ==========================================
    # Guardrail & Safety Metrics
    # ==========================================
    verdict: Mapped[Verdict] = mapped_column(
        PG_ENUM(Verdict, name="verdict"), 
        nullable=False, 
        index=True
    )
    
    corrections_applied: Mapped[list[str]] = mapped_column(
        ARRAY(String), 
        default=list
    )
    
    flagged_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(String), 
        default=list
    )
    
    risk_score: Mapped[float] = mapped_column(
        Float, 
        default=0.0
    )

    # ==========================================
    # Telemetry & Billing
    # ==========================================
    model_used: Mapped[str] = mapped_column(
        String, 
        nullable=False
    )
    
    latency_ms: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, 
        default=0
    )
    
    completion_tokens: Mapped[int] = mapped_column(
        Integer, 
        default=0
    )
    
    cost_usd: Mapped[float] = mapped_column(
        Float, 
        default=0.0
    )
    
    cache_hit: Mapped[bool] = mapped_column(
        Boolean, 
        default=False
    )

    # ==========================================
    # Relationships
    # ==========================================
    
    review_item: Mapped[ReviewItem | None] = relationship(
        back_populates="request_log",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )