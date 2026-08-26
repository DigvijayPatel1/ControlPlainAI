from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ApiKeyRotateResponse,
    AuthResponse,
    IssuedApiKey,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from app.services.auth_service import EmailAlreadyRegisteredError, InvalidCredentialsError, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


# ==================================================
# Register new user and provision resources
# ==================================================
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    try:
        user, token, raw_key = await auth_service.register(
            db,
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail=str(exc)) from exc

    return AuthResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        api_key=IssuedApiKey(principal_id=user.default_principal_id, raw_key=raw_key),
    )


# ==================================================
# Authenticate user and issue access token
# ==================================================
@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    try:
        user, token = await auth_service.authenticate(db, email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail=str(exc)
                        ) from exc

    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


# ==================================================
# Retrieve current authenticated user profile
# ==================================================
@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


# ==================================================
# Rotate API key for the authenticated user
# ==================================================
@router.post("/api-key/rotate", response_model=ApiKeyRotateResponse)
async def rotate_api_key(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyRotateResponse:
    
    raw_key = await auth_service.rotate_api_key(db, user=user)
    return ApiKeyRotateResponse(
        api_key=IssuedApiKey(principal_id=user.default_principal_id, raw_key=raw_key)
    )