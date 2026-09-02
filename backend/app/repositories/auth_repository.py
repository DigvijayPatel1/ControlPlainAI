from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.api_key import ApiKey


class AuthRepository:

    # ==================================================
    # Fetch user by email address
    # ==================================================
    @staticmethod
    async def get_user_by_email(
        db: AsyncSession, 
        email: str
    ) -> User | None:
        result = await db.execute(
            select(User)
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    # ==================================================
    # Fetch user by unique UUID
    # ==================================================
    @staticmethod
    async def get_user_by_id(
        db: AsyncSession, 
        user_id: UUID
    ) -> User | None:
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    # ==================================================
    # Add a new user to the database
    # ==================================================
    @staticmethod
    async def create_user(db: AsyncSession, user: User) -> User:
        db.add(user)
        await db.flush()
        return user

    # ==================================================
    # Retrieve API key record by principal ID
    # ==================================================
    @staticmethod
    async def get_api_key_by_principal_id(
        db: AsyncSession, principal_id: str) -> ApiKey | None:
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.principal_id == principal_id)
        )
        return result.scalar_one_or_none()


auth_repository = AuthRepository()