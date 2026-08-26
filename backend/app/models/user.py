"""ORM model for registered dashboard users (JWT authentication)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import TimestampMixin, UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String, 
        unique=True, 
        index=True, 
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String, 
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String, 
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        PG_ENUM(UserRole, name="user_role", create_type=False),
        default=UserRole.USER,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False
    )

    default_principal_id: Mapped[str | None] = mapped_column(
        String, 
        nullable=True
    )