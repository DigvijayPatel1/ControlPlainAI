"""FastAPI authentication dependencies."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import RateLimitExceeded, rate_limiter
from app.core.security import verify_api_key
from app.models.api_key import ApiKey
from app.models.common import PrincipalType, UserRole
from app.services.budget_service import BudgetExceededError, BudgetNotFoundError, budget_service


def extract_principal_id(api_key: str) -> str | None:
    if not api_key.startswith("cp_"):
        return None
    value = api_key[3:]
    principal_id, separator, _secret = value.rpartition("_")
    return principal_id if separator and principal_id else None


async def get_current_principal(
    db: AsyncSession = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> ApiKey:
    raw_key = (x_api_key or authorization or "").strip()
    if raw_key.lower().startswith("bearer "):
        raw_key = raw_key[7:].strip()
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key.")

    principal_id = extract_principal_id(raw_key)
    if principal_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
    result = await db.execute(select(ApiKey).where(ApiKey.principal_id == principal_id))
    principal = result.scalar_one_or_none()
    if principal is None or not verify_api_key(raw_key, principal.hashed_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
    if not principal.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is disabled.")
    if principal.expires_at and principal.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key has expired.")
    if principal.principal_type not in {PrincipalType.API_KEY, PrincipalType.EXTENSION}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unsupported principal.")
    principal.last_used_at = datetime.now(timezone.utc)
    return principal


def require_roles(*allowed_roles: UserRole):
    async def dependency(principal: ApiKey = Depends(get_current_principal)) -> ApiKey:
        if principal.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return principal
    return dependency


require_reviewer = require_roles(UserRole.REVIEWER, UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)


async def enforce_rate_limit(
    principal: ApiKey = Depends(get_current_principal),
) -> ApiKey:
    try:
        await rate_limiter.check(principal.principal_id)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.") from exc
    return principal


async def enforce_budget(
    principal: ApiKey = Depends(enforce_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    try:
        allowed = await budget_service.check_budget(
            db,
            principal_id=principal.principal_id,
            estimated_cost_usd=0.0,
        )
        if not allowed:
            raise BudgetExceededError("Monthly budget exceeded.")
    except BudgetNotFoundError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded.") from exc
    return principal


async def get_current_admin_dev() -> str:
    """Development placeholder; replace with role-based admin authentication."""
    return "admin-dev"
