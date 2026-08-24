import asyncio

from sqlalchemy import text

from app.core.database import engine


async def main():
    async with engine.connect() as connection:
        for table in ["api_keys", "budgets", "request_logs", "review_items"]:
            result = await connection.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )
            count = result.scalar_one()
            print(f"{table}: {count}")


if __name__ == "__main__":
    asyncio.run(main())