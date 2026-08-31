from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_reviewer
from app.core.database import get_db
from app.models.review_item import ReviewItem
from app.models.user import User

router = APIRouter(
    prefix="/v1/admin",
    tags=["reviews"],
)


@router.get("/reviews")
async def get_reviews(
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_reviewer),
):
    """Return unresolved review items, oldest first."""

    result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.resolved.is_(False))
        .order_by(ReviewItem.created_at.asc())
        .limit(limit)
    )

    reviews = result.scalars().all()

    return [
        {
            "review_id": review.id,
            "prompt": review.prompt,
            "proposed_response": review.proposed_response,
            "flagged_reason": review.flagged_reason,
            "risk_score": review.risk_score,
            "created_at": review.created_at,
        }
        for review in reviews
    ]