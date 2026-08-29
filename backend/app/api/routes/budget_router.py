"""Authenticated budget visibility for the current principal."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.budget_service import budget_service

router = APIRouter(prefix="/v1/budget", tags=["budget"])


@router.get("")
async def get_my_budget(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    if not user.default_principal_id:
        return {"configured": False}
    budget = await budget_service.get_budget(db, user.default_principal_id)
    if budget is None:
        return {"configured": False}
    return {
        "configured": True,
        "monthly_limit_usd": budget.monthly_limit_usd,
        "spent_usd": budget.spent_usd,
        "remaining_usd": max(0.0, budget.monthly_limit_usd - budget.spent_usd),
        "request_count": budget.request_count,
        "blocked_count": budget.blocked_count,
        "period_start": budget.period_start,
        "period_end": budget.period_end,
    }
