import asyncio

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.api_key import ApiKey
from app.models.budget import Budget

DEV_PRINCIPAL_IDS = ("dev-user", "demo_user")


async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Budget).where(
                Budget.principal_id.in_(DEV_PRINCIPAL_IDS)
            )
        )

        await session.execute(
            delete(ApiKey).where(
                ApiKey.principal_id.in_(DEV_PRINCIPAL_IDS)
            )
        )

        await session.commit()

    print("Development API key and budget removed.")


if __name__ == "__main__":
    asyncio.run(main())