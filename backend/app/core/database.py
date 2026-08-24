from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


DATABASE_URL = settings.DATABASE_URL


try:
    engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG, future=True)
except ModuleNotFoundError:
    # Keep pure unit-test imports usable when optional database drivers are absent.
    engine = None


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:

    if engine is None:
        raise RuntimeError("The configured database driver is not installed.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()