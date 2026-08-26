"""Create a development API key and print the raw secret once."""

from __future__ import annotations

import asyncio

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.api_key import ApiKey
from app.models.common import PrincipalType, SecurityPolicy, UserRole
from app.services.api_key_service import api_key_service


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(ApiKey).where(ApiKey.principal_id == "demo_user")
        )

        _api_key, raw_key = await api_key_service.create(
            db=db,
            principal_id="demo_user",
            owner_name="Demo User",
            principal_type=PrincipalType.API_KEY,
            role=UserRole.ADMIN,
            security_policy=SecurityPolicy.MONITOR,
        )
        await db.commit()
        print(raw_key)


if __name__ == "__main__":
    asyncio.run(main())
