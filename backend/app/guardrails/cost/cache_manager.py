"""Async-safe in-memory TTL cache for a single process development deployment."""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass


@dataclass(slots=True)
class _CacheEntry:
    value: str
    expires_at: float


class SemanticCache:
    """Exact normalized matching now; its API can later be backed by Redis/vector search."""

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 1_000) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def key_for(*parts: str | None) -> str:
        normalized = "\x1f".join((part or "").strip().casefold() for part in parts)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                del self._entries[key]
                return None
            return entry.value

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            if len(self._entries) >= self.max_entries:
                expired = [key for key, item in self._entries.items() if item.expires_at <= time.monotonic()]
                for expired_key in expired:
                    del self._entries[expired_key]
                if len(self._entries) >= self.max_entries:
                    del self._entries[next(iter(self._entries))]
            self._entries[key] = _CacheEntry(value, time.monotonic() + self.ttl_seconds)


cache = SemanticCache()
