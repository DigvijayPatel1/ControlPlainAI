from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

class Base(DeclarativeBase):
    pass


DATABASE_URL = str(settings.DATABASE_URL)


def setup_engine() -> AsyncEngine | None:
    try:
        return create_async_engine(
            DATABASE_URL,
            echo=settings.DEBUG,    
            future=True,
            pool_size=20,           
            max_overflow=10,        
            pool_pre_ping=True,     
            pool_recycle=3600,      
        )
    except ModuleNotFoundError:
        return None

engine = setup_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:

    if engine is None:
        raise RuntimeError("The configured database driver is not installed.")

    async with AsyncSessionLocal() as session:
        try:
            yield session

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()