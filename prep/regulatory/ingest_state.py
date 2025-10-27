"""Shared helpers for the regulatory ingestion workflow."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from prep.cache import get_redis
from prep.regulatory import RegulatoryChangeDetector

STATUS_CACHE_KEY = "reg_ingest:status"
SNAPSHOT_CACHE_KEY = "reg_ingest:snapshot"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _decode_payload(payload: Any) -> str | None:
    if payload is None:
        return None
    if isinstance(payload, bytes):
        return payload.decode("utf-8")
    if isinstance(payload, str):
        return payload
    return None


async def store_status(status: Mapping[str, Any], *, ttl: int = CACHE_TTL_SECONDS) -> None:
    """Persist the latest ingestion run metadata to the shared cache."""

    redis = await get_redis()
    serializable = {key: _serialize(value) for key, value in status.items()}
    await redis.setex(STATUS_CACHE_KEY, ttl, json.dumps(serializable))


async def fetch_status() -> dict[str, Any]:
    """Retrieve the most recent ingestion metadata from the cache."""

    redis = await get_redis()
    payload = _decode_payload(await redis.get(STATUS_CACHE_KEY))
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


async def store_document_snapshot(
    documents: Sequence[Mapping[str, str]], *, ttl: int = CACHE_TTL_SECONDS
) -> None:
    """Persist a lightweight snapshot of regulation documents for change detection."""

    redis = await get_redis()
    await redis.setex(SNAPSHOT_CACHE_KEY, ttl, json.dumps(list(documents)))


async def fetch_document_snapshot() -> list[dict[str, str]]:
    """Load the previously stored document snapshot from the cache."""

    redis = await get_redis()
    payload = _decode_payload(await redis.get(SNAPSHOT_CACHE_KEY))
    if not payload:
        return []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    snapshots: list[dict[str, str]] = []
    for item in data:
        if isinstance(item, dict):
            snapshots.append({str(key): str(value) for key, value in item.items()})
    return snapshots


async def record_document_changes(documents: Sequence[Mapping[str, str]]) -> int:
    """Update the cached snapshot and return the number of detected document changes."""

    detector = RegulatoryChangeDetector()
    previous = await fetch_document_snapshot()
    if previous:
        detector.previous_versions["regulations"] = (
            detector.hash_regulations(previous),
            previous,
        )
    changes = await detector.detect_changes(documents, "regulations")
    await store_document_snapshot(documents)
    return len(changes)


__all__ = [
    "store_status",
    "fetch_status",
    "store_document_snapshot",
    "fetch_document_snapshot",
    "record_document_changes",
]
