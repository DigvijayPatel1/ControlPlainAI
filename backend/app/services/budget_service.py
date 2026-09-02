"""Budget and spend enforcement without transaction commits."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.common import PrincipalType


class BudgetExceededError(Exception):
    """Raised when a request would exceed the configured budget."""


class BudgetNotFoundError(Exception):
    """Raised when a principal has no configured budget."""

    def __init__(self, principal_id: str) -> None:
        super().__init__(f"No budget configured for principal '{principal_id}'.")


class BudgetService:
    async def get_budget(self, db: AsyncSession, principal_id: str) -> Budget | None:
        result = await db.execute(select(Budget).where(Budget.principal_id == principal_id))
        return result.scalar_one_or_none()

    async def require_budget(self, db: AsyncSession, principal_id: str) -> Budget:
        budget = await self.get_budget(db, principal_id)
        if budget is None:
            raise BudgetNotFoundError(principal_id)
        return budget

    async def create_budget(
        self,
        db: AsyncSession,
        *,
        principal_id: str,
        principal_type: PrincipalType,
        monthly_limit_usd: float,
    ) -> Budget:
        if monthly_limit_usd < 0:
            raise ValueError("monthly_limit_usd cannot be negative.")
        if await self.get_budget(db, principal_id) is not None:
            raise ValueError("A budget already exists for this principal.")
        budget = Budget(
            id=uuid.uuid4(),
            principal_id=principal_id,
            principal_type=principal_type,
            monthly_limit_usd=monthly_limit_usd,
            spent_usd=0.0,
            period_start=datetime.now(timezone.utc),
            request_count=0,
            blocked_count=0,
        )
        db.add(budget)
        await db.flush()
        return budget

    async def check_budget(
        self,
        db: AsyncSession,
        *,
        principal_id: str,
        estimated_cost_usd: float,
    ) -> bool:
        if estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd cannot be negative.")
        budget = await self.require_budget(db, principal_id)
        return budget.spent_usd + estimated_cost_usd <= budget.monthly_limit_usd

    async def enforce_budget(
        self,
        db: AsyncSession,
        *,
        principal_id: str,
        estimated_cost_usd: float,
    ) -> Budget:
        if estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd cannot be negative.")
        result = await db.execute(
            select(Budget).where(Budget.principal_id == principal_id).with_for_update()
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            raise BudgetNotFoundError(principal_id)
        if budget.spent_usd + estimated_cost_usd > budget.monthly_limit_usd:
            budget.blocked_count += 1
            await db.flush()
            raise BudgetExceededError("Request exceeds the configured budget.")
        return budget

    async def record_spend(self, db: AsyncSession, *, principal_id: str, cost_usd: float) -> Budget:
        if cost_usd < 0:
            raise ValueError("cost_usd cannot be negative.")
        budget = await self.require_budget(db, principal_id)
        budget.spent_usd += cost_usd
        budget.request_count += 1
        await db.flush()
        return budget

    async def record_blocked_request(self, db: AsyncSession, *, principal_id: str) -> Budget:
        budget = await self.require_budget(db, principal_id)
        budget.blocked_count += 1
        await db.flush()
        return budget

    async def reset_budget(
        self,
        db: AsyncSession,
        *,
        principal_id: str,
        period_end: datetime | None = None,
    ) -> Budget:
        budget = await self.require_budget(db, principal_id)
        budget.spent_usd = 0.0
        budget.request_count = 0
        budget.blocked_count = 0
        budget.period_start = datetime.now(timezone.utc)
        budget.period_end = period_end
        await db.flush()
        return budget


budget_service = BudgetService()
