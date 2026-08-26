import asyncio

from sqlalchemy import text

from app.core.database import engine


async def main():
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        print("Database connection OK:", result.scalar())


asyncio.run(main())