"""Publish metadata-only ControlPlane events through Redis."""

from __future__ import annotations

from app.services.redis_service import redis_service

REVIEW_CHANNEL = "controlplane:review"
REQUEST_CHANNEL = "controlplane:requests"
ALERT_CHANNEL = "controlplane:alerts"


class NotificationService:
    async def notify_review(self, *, review_id: str, principal_id: str, reason: str, risk_score: float) -> None:
        await redis_service.publish(REVIEW_CHANNEL, {
            "type": "review_created", "review_id": review_id,
            "principal_id": principal_id, "reason": reason, "risk_score": risk_score,
        })

    async def notify_request(
        self, *, principal_id: str, request_id: str, verdict: str,
        risk_score: float, tokens_saved: int, savings_usd: float,
    ) -> None:
        await redis_service.publish(REQUEST_CHANNEL, {
            "type": "request_completed", "principal_id": principal_id,
            "request_id": request_id, "verdict": verdict, "risk_score": risk_score,
            "tokens_saved": tokens_saved, "savings_usd": savings_usd,
        })

    async def notify_alert(self, *, principal_id: str, alert_type: str, message: str) -> None:
        await redis_service.publish(ALERT_CHANNEL, {
            "type": "alert", "principal_id": principal_id,
            "alert_type": alert_type, "message": message,
        })


notification_service = NotificationService()
