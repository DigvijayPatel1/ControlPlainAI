from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.common import PrincipalType, ChatbotCategory, SecurityPolicy


class ApiKeyCreate(BaseModel):
    owner_name: str
    chatbot_category: Optional[ChatbotCategory] = None
    security_policy: SecurityPolicy = SecurityPolicy.MONITOR


class ApiKeyCreateResponse(BaseModel):
    """Returned exactly once, at creation time. The raw secret is never
    retrievable again — only its hash is stored server-side."""

    principal_id: str
    raw_secret: str
    principal_type: PrincipalType = PrincipalType.API_KEY


class EnrollmentTokenRequest(BaseModel):
    entra_object_id: str
    owner_name: str
    chatbot_category: ChatbotCategory


class EnrollmentTokenResponse(BaseModel):
    principal_id: str
    enrollment_token: str
    expires_at: datetime


class ApiKeyStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    principal_id: str
    principal_type: PrincipalType
    owner_name: str
    security_policy: SecurityPolicy
    active: bool
    last_used_at: Optional[datetime] = None