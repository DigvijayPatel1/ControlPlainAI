from __future__ import annotations

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.common import PrincipalType, SecurityPolicy, UserRole
from app.models.user import User
from app.services.api_key_service import api_key_service
from app.services.budget_service import budget_service
from app.repositories.auth_repository import auth_repository


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


# ==================================================
# Generate unique principal ID slug from email
# ==================================================
def _slugify_principal(email: str) -> str:
    local_part = email.split("@", 1)[0].lower()
    slug = re.sub(
        r"[^a-z0-9]+", "-", 
        local_part
    ).strip("-") or "user"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


class AuthService:

    # ==================================================
    # Register a new user and initialize resources
    # ==================================================
    async def register(
        self,
        db: AsyncSession,
        *,
        email: str,
        full_name: str,
        password: str,
    ) -> tuple[User, str, str]:
        
        existing_user = await auth_repository.get_user_by_email(db, email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError(f"Email '{email}' is already registered.")

        principal_id = _slugify_principal(email)

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.USER,
            is_active=True,
            default_principal_id=principal_id,
        )
        
        await auth_repository.create_user(db, user)

        _api_key, raw_key = await api_key_service.create(
            db=db,
            principal_id=principal_id,
            owner_name=full_name,
            principal_type=PrincipalType.API_KEY,
            role=UserRole.USER,
            security_policy=SecurityPolicy.MONITOR,
        )

        await budget_service.create_budget(
            db,
            principal_id=principal_id,
            principal_type=PrincipalType.API_KEY,
            monthly_limit_usd=settings.DEFAULT_MONTHLY_BUDGET_USD,
        )

        await db.commit()
        await db.refresh(user)

        token = create_access_token(
            str(user.id), 
            extra_claims={"email": user.email, "role": user.role.value}
        )
        return user, token, raw_key

    # ==================================================
    # Authenticate user credentials and issue token
    # ==================================================
    async def authenticate(
        self, 
        db: AsyncSession, 
        *, 
        email: str, 
        password: str
    ) -> tuple[User, str]:
        
        user = await auth_repository.get_user_by_email(db, email)
        
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")
        if not user.is_active:
            raise InvalidCredentialsError("This account has been disabled.")

        token = create_access_token(
            str(user.id), 
            extra_claims={"email": user.email, "role": user.role.value}
        )
        return user, token

    # ==================================================
    # Retrieve user by string ID
    # ==================================================
    async def get_user_by_id(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> User:
        try:
            uid = uuid.UUID(user_id)
        except ValueError as exc:
            raise UserNotFoundError(user_id) from exc
            
        user = await auth_repository.get_user_by_id(db, uid)
        
        if user is None:
            raise UserNotFoundError(user_id)
        return user

    # ==================================================
    # Rotate and issue a brand new API key
    # ==================================================
    async def rotate_api_key(
        self, 
        db: AsyncSession, 
        *, 
        user: User
    ) -> str:
        
        if user.default_principal_id:
            old_key = await auth_repository.get_api_key_by_principal_id(
                db, 
                user.default_principal_id
            )
            
            if old_key is not None:
                old_key.active = False

        principal_id = _slugify_principal(user.email)
        _api_key, raw_key = await api_key_service.create(
            db=db,
            principal_id=principal_id,
            owner_name=user.full_name,
            principal_type=PrincipalType.API_KEY,
            role=UserRole.USER,
            security_policy=SecurityPolicy.MONITOR,
        )
        
        await budget_service.create_budget(
            db,
            principal_id=principal_id,
            principal_type=PrincipalType.API_KEY,
            monthly_limit_usd=settings.DEFAULT_MONTHLY_BUDGET_USD,
        )
        
        user.default_principal_id = principal_id
        await db.commit()
        return raw_key


auth_service = AuthService()