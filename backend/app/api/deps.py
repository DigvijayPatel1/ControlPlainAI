"""FastAPI authentication dependencies."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_db
from app.core.rate_limit import RateLimitExceeded, rate_limiter
from app.core.security import API_KEY_PREFIX, decode_access_token, verify_api_key
from app.models.api_key import ApiKey
from app.models.common import PrincipalType
from app.models.user import User
from app.services.budget_service import BudgetExceededError, BudgetNotFoundError, budget_service
from app.services.auth_service import UserNotFoundError, auth_service
from app.repositories.auth_repository import auth_repository


_bearer_scheme = HTTPBearer(auto_error=False)


# ==================================================
# Extract principal ID from raw API key string
# ==================================================
def extract_principal_id(api_key: str) -> str | None:
    if not api_key.startswith("cp_"):
        return None
    value = api_key[3:]
    principal_id, separator, _secret = value.rpartition("_")
    return principal_id if separator and principal_id else None


# ==================================================
# Resolve the caller's principal (API key or JWT)
# ==================================================
async def get_current_principal(
    db: AsyncSession = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> ApiKey:
    raw_key = (x_api_key or authorization or "").strip()
    if raw_key.lower().startswith("bearer "):
        raw_key = raw_key[7:].strip()
        
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing credentials."
        )

    # Route to JWT logic if it doesn't start with the API key prefix
    if not raw_key.startswith(API_KEY_PREFIX):
        return await _resolve_principal_from_jwt(db, raw_key)

    # Extract principal_id for API keys
    principal_id = extract_principal_id(raw_key)
    if principal_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid API key."
        )

    principal = await auth_repository.get_api_key_by_principal_id(db, principal_id)
    
    if principal is None or not verify_api_key(raw_key, principal.hashed_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid API key."
        )
    
    _assert_principal_usable(principal)
    principal.last_used_at = datetime.now(timezone.utc)
    return principal


# ==================================================
# Resolve principal from a JWT payload
# ==================================================
async def _resolve_principal_from_jwt(db: AsyncSession, token: str) -> ApiKey:
    payload = decode_access_token(token)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired session."
        )

    try:
        user = await auth_service.get_user_by_id(db, payload["sub"])
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User not found."
        ) from exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This account has been disabled."
        )
    if not user.default_principal_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No API key provisioned for this account."
        )

    principal = await auth_repository.get_api_key_by_principal_id(db, user.default_principal_id)
    
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No API key provisioned for this account."
        )

    _assert_principal_usable(principal)

    principal.role = user.role
    principal.last_used_at = datetime.now(timezone.utc)
    return principal


# ==================================================
# Validate that the principal is active and valid
# ==================================================
def _assert_principal_usable(principal: ApiKey) -> None:
    if not principal.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="API key is disabled."
        )
    if principal.expires_at and principal.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="API key has expired."
        )
    if principal.principal_type not in {PrincipalType.API_KEY, PrincipalType.EXTENSION}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unsupported principal."
        )


# ==================================================
# Enforce rate limiting for the principal
# ==================================================
async def enforce_rate_limit(
    principal: ApiKey = Depends(get_current_principal),
) -> ApiKey:
    try:
        await rate_limiter.check(principal.principal_id)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded."
        ) from exc
    return principal


# ==================================================
# Enforce budget limits for the principal
# ==================================================
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
        raise HTTPException(
            status_code=403, 
            detail=str(exc)
        ) from exc
    except BudgetExceededError as exc:
        raise HTTPException(
            status_code=402, 
            detail="Monthly budget exceeded."
        ) from exc
    return principal


# ==================================================
# Authenticate dashboard user via JWT
# ==================================================
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing bearer token."
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired token."
        )

    try:
        user = await auth_service.get_user_by_id(db, payload["sub"])
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User not found."
        ) from exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="This account has been disabled."
        )
    return user


# Single-user app: the authenticated dashboard user is the only valid identity.
require_reviewer = get_current_user