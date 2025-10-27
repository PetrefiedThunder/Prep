"""Database loader utilities for regulatory documents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models.orm import RegDoc

_REQUIRED_FIELDS = {"jurisdiction", "code_section", "requirement_text", "sha256_hash"}
_OPTIONAL_FIELDS = {"effective_date", "citation_url"}


def _coerce_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:  # pragma: no cover - validation occurs earlier in pipeline
            raise ValueError(f"Invalid effective_date value: {value!r}") from exc
    raise ValueError(f"Unsupported effective_date type: {type(value)!r}")


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    missing = _REQUIRED_FIELDS - row.keys()
    if missing:
        raise ValueError(f"RegDoc row missing required fields: {sorted(missing)}")

    normalized: dict[str, Any] = {field: row[field] for field in _REQUIRED_FIELDS}
    if not normalized["sha256_hash"]:
        raise ValueError("sha256_hash must be non-empty")

    for field in _OPTIONAL_FIELDS:
        if field in row and row[field] not in (None, ""):
            normalized[field] = row[field]

    if "effective_date" in normalized:
        normalized["effective_date"] = _coerce_date(normalized["effective_date"])

    return normalized


async def load_regdocs(session: AsyncSession, rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """UPSERT the provided rows into ``reg_docs``."""

    summary = {"inserted": 0, "updated": 0, "skipped": 0}
    if not rows:
        return summary

    for row in rows:
        normalized = _normalize_row(row)
        sha_hash = normalized["sha256_hash"]

        existing = (
            await session.execute(select(RegDoc).where(RegDoc.sha256_hash == sha_hash))
        ).scalar_one_or_none()

        if existing is None:
            session.add(RegDoc(**normalized))
            summary["inserted"] += 1
            continue

        changed = False
        for key, value in normalized.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True

        if changed:
            summary["updated"] += 1
        else:
            summary["skipped"] += 1

    await session.flush()
    return summary


__all__ = ["load_regdocs"]
