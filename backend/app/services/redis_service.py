"""Optional Redis service for notifications and distributed coordination."""

from __future__ import annotations

import json
from typing import Any

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - optional local dependency
    redis = None  # type: ignore[assignment]

from app.core.config import settings


class RedisService:
    def __init__(self) -> None:
        self._client: Any = None

    @property
    def configured(self) -> bool:
        return redis is not None and bool(settings.REDIS_URL)

    async def connect(self) -> None:
        if self._client is not None:
            return
        if redis is None:
            raise RuntimeError("Redis support is not installed.")
        if not settings.REDIS_URL:
            raise RuntimeError("REDIS_URL is not configured.")
        self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, key: str) -> str | None:
        await self.connect()
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        await self.connect()
        await self._client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self.connect()
        await self._client.delete(key)

    async def increment(self, key: str, amount: int = 1, expire: int | None = None) -> int:
        await self.connect()
        value = await self._client.incrby(key, amount)
        if expire is not None and value == amount:
            await self._client.expire(key, expire)
        return int(value)

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        await self.connect()
        await self._client.publish(channel, json.dumps(event))

    async def health_check(self) -> bool:
        try:
            await self.connect()
            return bool(await self._client.ping())
        except Exception:
            return False


redis_service = RedisService()
