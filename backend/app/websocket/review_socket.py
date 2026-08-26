"""Live metadata events for the ControlPlane dashboard."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.notification_service import ALERT_CHANNEL, REQUEST_CHANNEL, REVIEW_CHANNEL
from app.services.redis_service import redis_service

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/controlplane")
async def controlplane_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        await redis_service.connect()
        client = redis_service._client
        if client is None:
            await websocket.send_json({"type": "error", "message": "Redis is unavailable."})
            return
        pubsub = client.pubsub()
        await pubsub.subscribe(REVIEW_CHANNEL, REQUEST_CHANNEL, ALERT_CHANNEL)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and isinstance(message.get("data"), str):
                    await websocket.send_text(message["data"])
                await asyncio.sleep(0.05)
        finally:
            await pubsub.unsubscribe(REVIEW_CHANNEL, REQUEST_CHANNEL, ALERT_CHANNEL)
            await pubsub.close()
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=1011)
