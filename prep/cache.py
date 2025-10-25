"""Redis cache utilities for analytics endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Protocol

try:  # pragma: no cover - optional dependency import guard
    from redis.asyncio import Redis  # type: ignore
except ImportError:  # pragma: no cover - fallback when redis is unavailable
    Redis = None  # type: ignore

logger = logging.getLogger(__name__)

from prep.settings import get_settings

_CACHE_CLIENT: "RedisProtocol" | None = None


class RedisProtocol(Protocol):
    """Protocol describing the Redis operations used by the service."""

    async def get(self, key: str) -> Any:
        ...

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        ...


class _MemoryRedis:
    """In-memory Redis fallback used during local testing."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        async with self._lock:
            payload = self._store.get(key)
            if not payload:
                return None
            expires_at, value = payload
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    async def setex(self, key: str, ttl: int, value: Any) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl, value)


async def get_redis() -> RedisProtocol:
    """FastAPI dependency returning a Redis client or in-memory fallback."""

    global _CACHE_CLIENT
    if _CACHE_CLIENT is not None:
        return _CACHE_CLIENT

    settings = get_settings()

    if Redis is not None:  # pragma: no branch - single initialization path
        try:
            _CACHE_CLIENT = Redis.from_url(
                str(settings.redis_url), encoding="utf-8", decode_responses=True
            )
            return _CACHE_CLIENT
        except Exception:  # pragma: no cover - network failures
            logger.exception(
                "Failed to initialize Redis client",
                extra={"redis_url": str(settings.redis_url)},
            )

    logger.warning("Redis dependency unavailable, falling back to in-memory cache")
    _CACHE_CLIENT = _MemoryRedis()
    return _CACHE_CLIENT


__all__ = ["get_redis", "RedisProtocol"]

