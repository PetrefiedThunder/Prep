"""Helpers for persisting regulatory documents."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from prep.cache import RedisProtocol
from prep.regulatory.models import RegDoc

logger = logging.getLogger(__name__)

_REGDOC_FIELDS = {
    "sha256_hash",
    "jurisdiction",
    "country_code",
    "state",
    "state_province",
    "city",
    "doc_type",
    "title",
    "summary",
    "source_url",
    "raw_payload",
}


def _normalize_regdoc(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "sha256_hash" not in payload or not payload["sha256_hash"]:
        raise ValueError("RegDoc payload missing required 'sha256_hash'")

    normalized = {
        key: payload[key] for key in _REGDOC_FIELDS if key in payload and payload[key] is not None
    }
    normalized.setdefault("country_code", "US")
    if "state_province" not in normalized and "state" in normalized:
        normalized["state_province"] = payload.get("state")
    normalized.setdefault("raw_payload", dict(payload))
    return normalized


def _invalidate_rules_cache(redis_client: RedisProtocol) -> None:
    """Invalidate cached regulatory rule entries stored in Redis."""

    async def _invalidate() -> None:
        try:
            keys = await redis_client.keys("rules:*")
        except Exception:
            logger.exception("Failed to enumerate regulatory rule cache keys")
            return

        if not keys:
            return

        try:
            await redis_client.delete(*keys)
        except Exception:
            logger.exception("Failed to delete regulatory rule cache keys", extra={"keys": keys})
            return

        logger.info(
            "Invalidated %d regulatory rule cache keys",
            len(keys),
            extra={"invalidated_keys": sorted(keys)},
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.run(_invalidate())
        except Exception:
            logger.exception("Unhandled error invalidating regulatory rule cache")
    else:
        task = loop.create_task(_invalidate())

        def _log_task_result(fut: asyncio.Future[None]) -> None:
            try:
                fut.result()
            except Exception:
                logger.exception("Unhandled error invalidating regulatory rule cache")

        task.add_done_callback(_log_task_result)


def load_regdoc(
    session: Session,
    regdocs: list[dict[str, Any]],
    *,
    redis_client: RedisProtocol | None = None,
) -> int:
    """Insert or update :class:`RegDoc` rows based on their SHA-256 hash."""

    if not regdocs:
        return 0

    inserted = 0
    updated = 0
    for entry in regdocs:
        normalized = _normalize_regdoc(entry)
        sha_hash = normalized["sha256_hash"]

        existing = session.execute(
            select(RegDoc).where(RegDoc.sha256_hash == sha_hash)
        ).scalar_one_or_none()

        if existing is None:
            session.add(RegDoc(**normalized))
            inserted += 1
        else:
            changed = False
            for key, value in normalized.items():
                if getattr(existing, key) != value:
                    setattr(existing, key, value)
                    changed = True
            if changed:
                updated += 1

    session.flush()
    if redis_client is not None and (inserted or updated):
        _invalidate_rules_cache(redis_client)
    return inserted


__all__ = ["load_regdoc"]
