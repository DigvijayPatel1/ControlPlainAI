import asyncio

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.api_key import ApiKey
from app.models.budget import Budget


async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Budget).where(
                Budget.principal_id == "dev-user"
            )
        )

        await session.execute(
            delete(ApiKey).where(
                ApiKey.principal_id == "dev-user"
            )
        )

        await session.commit()

    print("Development API key and budget removed.")


if __name__ == "__main__":
    asyncio.run(main())