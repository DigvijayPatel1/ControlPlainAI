"""ORM model for principal credentials — covers both direct-API virtual keys
and Entra ID enrollment tokens issued to the browser extension."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import ChatbotCategory, PrincipalType, SecurityPolicy, TimestampMixin, UserRole


class ApiKey(Base, TimestampMixin):

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    # ==========================================
    # Identity & Ownership
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

    owner_name: Mapped[str] = mapped_column(
        String, 
        nullable=False
    )
    
    # Set only for EXTENSION principal types
    entra_object_id: Mapped[str | None] = mapped_column(
        String, 
        nullable=True
    )

    # ==========================================
    # Security & Policy
    # ==========================================
    # Never store the raw secret
    hashed_secret: Mapped[str] = mapped_column(
        String, 
        nullable=False
    )
    
    security_policy: Mapped[SecurityPolicy] = mapped_column(
        PG_ENUM(SecurityPolicy, name="security_policy"), 
        default=SecurityPolicy.MONITOR
    )

    # ==========================================
    # Configuration
    # ==========================================
    chatbot_category: Mapped[ChatbotCategory | None] = mapped_column(
        PG_ENUM(ChatbotCategory, name="chatbot_category"), 
        nullable=True
    )

    # ==========================================
    # State & Lifecycle
    # ==========================================
    active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )

    role: Mapped[UserRole] = mapped_column(
        PG_ENUM(UserRole, name="user_role"), default=UserRole.USER, nullable=False
    )