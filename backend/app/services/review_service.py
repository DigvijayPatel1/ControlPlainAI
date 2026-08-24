"""Business logic for creating and resolving human-review items."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.guardrails.contracts import PipelineResult
from app.models.common import ReviewAction
from app.repositories.review_item_repositories import (
    create_review_item,
    get_by_id,
    list_pending,
    resolve_review,
)


class ReviewNotFoundError(Exception):
    """Raised when a review item does not exist."""


class ReviewAlreadyResolvedError(Exception):
    """Raised when an already-resolved item is modified."""


class ReviewService:
    async def create_review(
        self,
        *,
        db: AsyncSession,
        request_log_id: UUID,
        prompt: str,
        proposed_response: str,
        result: PipelineResult,
    ):
        return await create_review_item(
            db,
            request_log_id=request_log_id,
            prompt=prompt,
            proposed_response=proposed_response,
            flagged_reason="; ".join(result.reasons) or "manual_review_required",
            risk_score=result.risk_score,
        )

    async def get_pending(self, *, db: AsyncSession, limit: int = 100):
        return await list_pending(db, limit=max(1, min(limit, 500)))

    async def get_review(self, *, db: AsyncSession, review_id: UUID):
        item = await get_by_id(db, review_id)
        if item is None:
            raise ReviewNotFoundError(f"Review {review_id} not found.")
        return item

    async def resolve(
        self,
        *,
        db: AsyncSession,
        review_id: UUID,
        reviewer_id: str,
        action: ReviewAction,
        final_response: str,
    ):
        item = await self.get_review(db=db, review_id=review_id)
        if item.resolved:
            raise ReviewAlreadyResolvedError("Review item has already been resolved.")
        if action is ReviewAction.APPROVE and not final_response:
            final_response = item.proposed_response
        return await resolve_review(
            db,
            review_id=review_id,
            action=action,
            final_response=final_response,
            resolved_by=reviewer_id,
        )


review_service = ReviewService()
