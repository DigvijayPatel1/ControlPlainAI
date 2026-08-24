"""Periodic worker for expired budget periods."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.budget import Budget


async def reset_expired_budgets() -> int:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Budget).where(Budget.period_end.is_not(None), Budget.period_end <= now))
        budgets = result.scalars().all()
        for budget in budgets:
            budget.spent_usd = 0.0
            budget.request_count = 0
            budget.blocked_count = 0
            budget.period_start = now
            budget.period_end = None
        await db.commit()
        return len(budgets)


async def run() -> None:
    while True:
        try:
            await reset_expired_budgets()
        except Exception as exc:
            print(f"Budget worker error: {exc}")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run())
