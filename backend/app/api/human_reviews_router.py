"""API endpoints for human-review queue operations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_reviewer
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.models.common import ReviewAction
from app.schemas.review_item import ReviewDecisionRequest, ReviewDecisionResult, ReviewItem
from app.services.review_service import (
    ReviewAlreadyResolvedError,
    ReviewNotFoundError,
    review_service,
)

router = APIRouter(prefix="/v1/admin/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewItem])
async def get_reviews(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(require_reviewer),
) -> list[ReviewItem]:
    """Return unresolved review items, oldest first."""
    return await review_service.get_pending(db=db, limit=limit)


@router.get("/{review_id}", response_model=ReviewItem)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(require_reviewer),
) -> ReviewItem:
    try:
        return await review_service.get_review(db=db, review_id=review_id)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Review item not found.") from exc


@router.post("/{review_id}/resolve", response_model=ReviewDecisionResult)
async def resolve_review(
    review_id: UUID,
    resolution: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
    principal: ApiKey = Depends(require_reviewer),
) -> ReviewDecisionResult:
    """Resolve a pending item using the demo reviewer identity."""
    try:
        item = await review_service.resolve(
            db=db,
            review_id=review_id,
            reviewer_id="demo-reviewer",
            action=resolution.action,
            final_response=resolution.edited_content or "",
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Review item not found.") from exc
    except ReviewAlreadyResolvedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    final_response = item.final_response or item.proposed_response
    return ReviewDecisionResult(
        review_id=item.id,
        action_taken=item.action_taken or ReviewAction.APPROVE,
        final_response=final_response,
        resolved_by=item.resolved_by or "demo-reviewer",
    )
