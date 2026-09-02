import asyncio

from sqlalchemy import text

from app.core.database import engine


async def main() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
        )

        tables = [row[0] for row in result]

        print("\nDatabase tables:")
        for table in tables:
            print(f"  - {table}")


if __name__ == "__main__":
    asyncio.run(main())