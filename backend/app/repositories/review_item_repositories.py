from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_item import ReviewItem
from app.models.common import ReviewAction
from app.models.request_log import RequestLog


async def create_review_item(
    db: AsyncSession,
    *,
    request_log_id: UUID,
    prompt: str,
    proposed_response: str,
    flagged_reason: str,
    risk_score: float,
) -> ReviewItem:
    item = ReviewItem(
        request_log_id=request_log_id,
        prompt=prompt,
        proposed_response=proposed_response,
        flagged_reason=flagged_reason,
        risk_score=risk_score,
        resolved=False,
    )

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item


async def get_by_id(
    db: AsyncSession,
    review_id: UUID,
) -> ReviewItem | None:
    result = await db.execute(
        select(ReviewItem).where(
            ReviewItem.id == review_id
        )
    )

    return result.scalar_one_or_none()


async def list_pending(
    db: AsyncSession,
    limit: int = 100,
) -> list[ReviewItem]:
    result = await db.execute(
        select(ReviewItem)
        .where(ReviewItem.resolved.is_(False))
        .order_by(ReviewItem.created_at.asc())
        .limit(limit)
    )

    return list(result.scalars().all())


async def has_approved_prompt(
    db: AsyncSession,
    *,
    prompt: str,
) -> bool:
    result = await db.execute(
        select(ReviewItem.id)
        .join(RequestLog, ReviewItem.request_log_id == RequestLog.id)
        .where(
            ReviewItem.prompt == prompt,
            ReviewItem.resolved.is_(True),
        )
        .limit(1)
    )

    return result.scalar_one_or_none() is not None


async def resolve_review(
    db: AsyncSession,
    *,
    review_id: UUID,
    action: ReviewAction,
    final_response: str,
    resolved_by: str,
) -> ReviewItem:
    item = await get_by_id(
        db,
        review_id,
    )

    if item is None:
        raise ValueError(
            f"Review {review_id} not found."
        )

    item.resolved = True
    item.resolved_at = datetime.now(timezone.utc)
    item.resolved_by = resolved_by
    item.action_taken = action
    item.final_response = final_response

    await db.commit()
    await db.refresh(item)

    return item