"""CRUD and query logic for ReviewItem."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common import ReviewAction
from app.models.review_item import ReviewItem


#----------------------------------------------------------
# ReviewItem repository functions
#----------------------------------------------------------

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
    )
    
    db.add(item)
    await db.flush()
    await db.refresh(item)
    
    return item


#----------------------------------------------------------
# ReviewItem repository functions
#----------------------------------------------------------

async def get_by_id(
    db: AsyncSession, 
    review_id: UUID
) -> ReviewItem | None:
    
    stmt = (
        select(ReviewItem)
        .where(ReviewItem.id == review_id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    
    return result.scalar_one_or_none()


#----------------------------------------------------------
# ReviewItem repository functions
#----------------------------------------------------------

async def list_pending(
    db: AsyncSession, 
    *, 
    limit: int = 50
) -> list[ReviewItem]:
    
    stmt = (
        select(ReviewItem)
        .where(ReviewItem.resolved.is_(False))
        .order_by(ReviewItem.created_at.asc())   # oldest first — first in, first reviewed
        .limit(limit)
    )
    result = await db.execute(stmt)
    
    return list(result.scalars().all())


#----------------------------------------------------------
# ReviewItem repository functions
#----------------------------------------------------------

async def resolve_review(
    db: AsyncSession,
    *,
    review_id: UUID,
    action: ReviewAction,
    final_response: str,
    resolved_by: str,
) -> ReviewItem | None:
    
    item = await get_by_id(db, review_id)
    if item is None:
        return None

    item.resolved = True
    item.resolved_at = datetime.now(timezone.utc)
    item.resolved_by = resolved_by
    item.action_taken = action
    item.final_response = final_response

    await db.flush()
    await db.refresh(item)
    
    return item