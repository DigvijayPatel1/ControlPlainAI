"""Publish metadata-only ControlPlane events through Redis.

Redis is optional everywhere else in this app (cache, rate limiter), so
notifications must be best-effort too: a missing/unreachable Redis must
never fail the request that triggered the notification.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.services.redis_service import redis_service

REVIEW_CHANNEL = "controlplane:review"
REQUEST_CHANNEL = "controlplane:requests"
ALERT_CHANNEL = "controlplane:alerts"

logger = get_logger(__name__)


class NotificationService:
    async def _publish(self, channel: str, event: dict) -> None:
        if not redis_service.configured:
            return
        try:
            await redis_service.publish(channel, event)
        except Exception:
            # Never let a notification failure fail the caller's request.
            logger.warning("Failed to publish %s event to Redis.", event.get("type"), exc_info=True)

    async def notify_review(self, *, review_id: str, principal_id: str, reason: str, risk_score: float) -> None:
        await self._publish(REVIEW_CHANNEL, {
            "type": "review_created", "review_id": review_id,
            "principal_id": principal_id, "reason": reason, "risk_score": risk_score,
        })

    async def notify_request(
        self, *, principal_id: str, request_id: str, verdict: str,
        risk_score: float, tokens_saved: int, savings_usd: float,
    ) -> None:
        await self._publish(REQUEST_CHANNEL, {
            "type": "request_completed", "principal_id": principal_id,
            "request_id": request_id, "verdict": verdict, "risk_score": risk_score,
            "tokens_saved": tokens_saved, "savings_usd": savings_usd,
        })

    async def notify_alert(self, *, principal_id: str, alert_type: str, message: str) -> None:
        await self._publish(ALERT_CHANNEL, {
            "type": "alert", "principal_id": principal_id,
            "alert_type": alert_type, "message": message,
        })


notification_service = NotificationService()