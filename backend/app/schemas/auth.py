from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.common import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    default_principal_id: str | None = None
    created_at: datetime


class IssuedApiKey(BaseModel):
    """Returned exactly once. The raw secret is never retrievable again."""

    principal_id: str
    raw_key: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    api_key: IssuedApiKey | None = None


class ApiKeyRotateResponse(BaseModel):
    api_key: IssuedApiKey