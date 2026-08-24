"""Republish pending review metadata for dashboard subscribers."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.request_log import RequestLog
from app.models.review_item import ReviewItem
from app.services.notification_service import notification_service


async def publish_pending_reviews() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ReviewItem, RequestLog)
            .join(RequestLog, ReviewItem.request_log_id == RequestLog.id)
            .where(ReviewItem.resolved.is_(False))
        )
        for review, request_log in result.all():
            await notification_service.notify_review(
                review_id=str(review.id), principal_id=request_log.principal_id,
                reason=review.flagged_reason, risk_score=review.risk_score,
            )


async def run() -> None:
    while True:
        try:
            await publish_pending_reviews()
        except Exception as exc:
            print(f"Review worker error: {exc}")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
