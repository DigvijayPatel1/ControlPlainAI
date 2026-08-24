from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.request_log import RequestLog
from app.models.review_item import ReviewItem

router = APIRouter(prefix="/api/requests", tags=["Requests"])


@router.get("")
async def list_requests(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RequestLog)
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
    )

    rows = result.scalars().all()

    return {
        "items": [
            {
                "id": str(row.id),
                "principal_id": row.principal_id,
                "model_used": row.model_used,
                "verdict": row.verdict.value
                if hasattr(row.verdict, "value")
                else row.verdict,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "cost_usd": row.cost_usd,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "count": len(rows),
    }


@router.get("/{request_id}")
async def get_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RequestLog).where(RequestLog.id == request_id)
    )

    request = result.scalar_one_or_none()

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Request not found.",
        )

    review_result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.request_log_id == request.id)
        .order_by(ReviewItem.created_at.desc())
    )

    reviews = review_result.scalars().all()

    return {
        "id": str(request.id),
        "principal_id": request.principal_id,
        "model_used": request.model_used,
        "verdict": request.verdict.value
        if hasattr(request.verdict, "value")
        else request.verdict,
        "prompt_tokens": request.prompt_tokens,
        "completion_tokens": request.completion_tokens,
        "cost_usd": request.cost_usd,
        "created_at": request.created_at,
        "reviews": [
            {
                "id": str(review.id),
                "request_log_id": str(review.request_log_id),
                "input_text": review.input_text,
                "output_text": review.output_text,
                "reason": review.reason,
                "score": review.score,
                "blocked": review.blocked,
                "created_at": review.created_at,
            }
            for review in reviews
        ],
    }