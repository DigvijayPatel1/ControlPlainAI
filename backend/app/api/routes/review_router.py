from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_reviewer
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.models.review_item import ReviewItem
from app.schemas.review_item import ReviewItemResponse, ReviewListResponse

router = APIRouter(
    prefix="/api/reviews",
    tags=["Reviews"],
)


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(require_reviewer),
):
    # Fetch paginated results
    result = await db.execute(
        select(ReviewItem)
        .order_by(ReviewItem.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.scalars().all()

    # FastAPI and Pydantic will automatically map the ORM rows to ReviewItemResponse
    return {
        "items": rows,
        "count": len(rows),
    }


@router.get("/{review_id}", response_model=ReviewItemResponse)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(require_reviewer),
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

    return review