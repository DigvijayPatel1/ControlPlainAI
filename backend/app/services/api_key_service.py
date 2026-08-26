"""API-key lifecycle service. Raw keys are returned only at creation time."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key
from app.models.api_key import ApiKey
from app.models.common import ChatbotCategory, PrincipalType, SecurityPolicy, UserRole


class ApiKeyService:
    async def create(
        self,
        *,
        db: AsyncSession,
        principal_id: str,
        owner_name: str,
        principal_type: PrincipalType,
        role: UserRole = UserRole.USER,
        security_policy: SecurityPolicy = SecurityPolicy.MONITOR,
        chatbot_category: ChatbotCategory | None = None,
        entra_object_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        raw_key, hashed_key = generate_api_key(principal_id)
        api_key = ApiKey(
            principal_id=principal_id,
            principal_type=principal_type,
            owner_name=owner_name,
            entra_object_id=entra_object_id,
            hashed_secret=hashed_key,
            role=role,
            security_policy=security_policy,
            chatbot_category=chatbot_category,
            active=True,
            expires_at=expires_at,
        )
        db.add(api_key)
        await db.flush()
        return api_key, raw_key


api_key_service = ApiKeyService()
