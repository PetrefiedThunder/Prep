"""Database loader utilities for regulatory documents."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from types import AsyncGeneratorType
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from prep.regulatory.models import RegDoc

_SYNC_REGDOC_FIELDS: set[str] = {
    "sha256_hash",
    "jurisdiction",
    "state",
    "city",
    "doc_type",
    "title",
    "summary",
    "source_url",
    "raw_payload",
}

_ASYNC_REQUIRED_FIELDS = {
    "jurisdiction",
    "code_section",
    "requirement_text",
    "sha256_hash",
}
_ASYNC_OPTIONAL_FIELDS = {"effective_date", "citation_url"}


def _normalize_sync_row(row: Mapping[str, Any]) -> dict[str, Any]:
    sha_hash = row.get("sha256_hash")
    if not sha_hash:
        raise ValueError("RegDoc payload missing required 'sha256_hash'")

    normalized = {
        key: row[key]
        for key in _SYNC_REGDOC_FIELDS
        if key in row and row[key] is not None
    }
    normalized.setdefault("raw_payload", dict(row))
    return normalized


def _coerce_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Unsupported effective_date type: {type(value)!r}")


def _normalize_async_row(row: Mapping[str, Any]) -> dict[str, Any]:
    missing = _ASYNC_REQUIRED_FIELDS - row.keys()
    if missing:
        raise ValueError(f"RegDoc row missing required fields: {sorted(missing)}")

    normalized: dict[str, Any] = {field: row[field] for field in _ASYNC_REQUIRED_FIELDS}
    if not normalized["sha256_hash"]:
        raise ValueError("sha256_hash must be non-empty")

    for field in _ASYNC_OPTIONAL_FIELDS:
        if field in row and row[field] not in (None, ""):
            normalized[field] = row[field]

    if "effective_date" in normalized:
        normalized["effective_date"] = _coerce_date(normalized["effective_date"])

    return normalized


def _load_regdocs_sync(session: Session, rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    summary = {"inserted": 0, "updated": 0, "skipped": 0}

    for row in rows:
        try:
            normalized = _normalize_sync_row(row)
        except ValueError:
            summary["skipped"] += 1
            continue

        sha_hash = normalized["sha256_hash"]
        existing = (
            session.execute(select(RegDoc).where(RegDoc.sha256_hash == sha_hash))
            .scalars()
            .one_or_none()
        )

        if existing is None:
            session.add(RegDoc(**normalized))
            summary["inserted"] += 1
            continue

        changed = False
        for key, value in normalized.items():
            if getattr(existing, key, None) != value:
                setattr(existing, key, value)
                changed = True

        if changed:
            summary["updated"] += 1
        else:
            summary["skipped"] += 1

    session.flush()
    return summary


async def _load_regdocs_async(
    session: AsyncSession, rows: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    summary = {"inserted": 0, "updated": 0, "skipped": 0}
    if not rows:
        return summary

    for row in rows:
        normalized = _normalize_async_row(row)

        sha_hash = normalized["sha256_hash"]
        existing = (
            await session.execute(select(RegDoc).where(RegDoc.sha256_hash == sha_hash))
        ).scalars().one_or_none()

        if existing is None:
            session.add(RegDoc(**normalized))
            summary["inserted"] += 1
            continue

        changed = False
        for key, value in normalized.items():
            if getattr(existing, key, None) != value:
                setattr(existing, key, value)
                changed = True

        if changed:
            summary["updated"] += 1
        else:
            summary["skipped"] += 1

    await session.flush()
    return summary


def load_regdocs(
    session: Session | AsyncSession, rows: Iterable[Mapping[str, Any]]
) -> dict[str, int] | Any:
    """Perform an UPSERT of :class:`RegDoc` rows in sync and async contexts."""

    if isinstance(session, AsyncSession):
        materialized_rows = list(rows)
        return _load_regdocs_async(session, materialized_rows)

    if isinstance(session, AsyncGeneratorType):
        materialized_rows = list(rows)

        async def _consume_generator() -> dict[str, int]:
            try:
                actual_session = await session.__anext__()
            except StopAsyncIteration as exc:  # pragma: no cover - defensive
                raise RuntimeError("Async session generator did not yield a session") from exc
            try:
                return await _load_regdocs_async(actual_session, materialized_rows)
            finally:
                with suppress(Exception):
                    await session.aclose()

        return _consume_generator()

    return _load_regdocs_sync(session, rows)


__all__ = ["load_regdocs"]
