"""Utilities for storing pricing refresh status in the shared cache."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from prep.cache import get_redis

STATUS_CACHE_KEY = "pricing_refresh:status"
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _decode(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return None


async def store_pricing_status(status: Mapping[str, Any], *, ttl: int = CACHE_TTL_SECONDS) -> None:
    """Persist the latest pricing refresh run metadata."""

    redis = await get_redis()
    serializable = {key: _serialize(value) for key, value in status.items()}
    await redis.setex(STATUS_CACHE_KEY, ttl, json.dumps(serializable))


async def fetch_pricing_status() -> dict[str, Any]:
    """Retrieve the cached pricing refresh metadata."""

    redis = await get_redis()
    payload = _decode(await redis.get(STATUS_CACHE_KEY))
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


__all__ = ["fetch_pricing_status", "store_pricing_status"]
