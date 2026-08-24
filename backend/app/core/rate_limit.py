"""Process-local rate limiter for a single backend instance."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.services.redis_service import redis_service


class RateLimitExceeded(Exception):
    """Raised when a principal exceeds its request window."""


@dataclass(slots=True)
class RateWindow:
    started_at: float
    requests: int = 0


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, RateWindow] = {}
        self._lock = asyncio.Lock()

    async def check(self, principal_id: str) -> None:
        if redis_service.configured:
            window = int(time.time() // self.window_seconds)
            count = await redis_service.increment(
                f"ratelimit:{principal_id}:{window}",
                expire=self.window_seconds + 2,
            )
            if count > self.max_requests:
                raise RateLimitExceeded("Rate limit exceeded.")
            return
        now = time.monotonic()
        async with self._lock:
            window = self._windows.get(principal_id)
            if window is None or now - window.started_at >= self.window_seconds:
                self._windows[principal_id] = RateWindow(now, 1)
                return
            if window.requests >= self.max_requests:
                raise RateLimitExceeded("Rate limit exceeded.")
            window.requests += 1

    async def reset(self, principal_id: str) -> None:
        async with self._lock:
            self._windows.pop(principal_id, None)

    async def cleanup(self) -> None:
        now = time.monotonic()
        async with self._lock:
            self._windows = {
                principal_id: window
                for principal_id, window in self._windows.items()
                if now - window.started_at < self.window_seconds
            }


rate_limiter = RateLimiter()
