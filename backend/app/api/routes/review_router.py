from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.review_item import ReviewItem

router = APIRouter(
    prefix="/api/reviews",
    tags=["Reviews"],
)


@router.get("")
async def list_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReviewItem)
        .order_by(ReviewItem.created_at.desc())
        .limit(limit)
    )

    rows = result.scalars().all()

    return {
        "items": [
            {
                "id": str(row.id),
                "request_log_id": str(row.request_log_id),
                "prompt": row.prompt,
                "proposed_response": row.proposed_response,
                "flagged_reason": row.flagged_reason,
                "risk_score": row.risk_score,
                "resolved": row.resolved,
                "resolved_at": row.resolved_at,
                "resolved_by": row.resolved_by,
                "action_taken": (
                    row.action_taken.value
                    if row.action_taken is not None
                    and hasattr(row.action_taken, "value")
                    else row.action_taken
                ),
                "final_response": row.final_response,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "count": len(rows),
    }


@router.get("/{review_id}")
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReviewItem).where(ReviewItem.id == review_id)
    )

    review = result.scalar_one_or_none()

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review item not found.",
        )

    return {
        "id": str(review.id),
        "request_log_id": str(review.request_log_id),
        "prompt": review.prompt,
        "proposed_response": review.proposed_response,
        "flagged_reason": review.flagged_reason,
        "risk_score": review.risk_score,
        "resolved": review.resolved,
        "resolved_at": review.resolved_at,
        "resolved_by": review.resolved_by,
        "action_taken": (
            review.action_taken.value
            if review.action_taken is not None
            and hasattr(review.action_taken, "value")
            else review.action_taken
        ),
        "final_response": review.final_response,
        "created_at": review.created_at,
    }