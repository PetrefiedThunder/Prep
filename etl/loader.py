"""Helpers for loading regulatory documents into the warehouse."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from prep.regulatory.models import RegDoc

# Columns that can be persisted on ``RegDoc`` records.
_REGDOC_FIELDS: set[str] = {
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


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and coerce incoming RegDoc payloads."""

    sha_hash = row.get("sha256_hash")
    if not sha_hash:
        raise ValueError("RegDoc payload missing required 'sha256_hash'")

    normalized = {
        key: row[key]
        for key in _REGDOC_FIELDS
        if key in row and row[key] is not None
    }
    normalized.setdefault("raw_payload", dict(row))
    return normalized


def load_regdocs(
    session: Session, rows: Iterable[Mapping[str, Any]]
) -> dict[str, int]:
    """Perform an UPSERT of :class:`RegDoc` records by ``sha256_hash``.

    Args:
        session: Active SQLAlchemy session connected to the target database.
        rows: Iterable of dictionaries (or mappings) describing RegDocs.

    Returns:
        A dictionary summarizing how many records were inserted, updated, or
        skipped during the load.
    """

    inserted = 0
    updated = 0
    skipped = 0

    for row in rows:
        try:
            normalized = _normalize_row(row)
        except ValueError:
            skipped += 1
            continue

        sha_hash = normalized["sha256_hash"]
        existing = session.execute(
            select(RegDoc).where(RegDoc.sha256_hash == sha_hash)
        ).scalar_one_or_none()

        if existing is None:
            # Insert new record
            doc = RegDoc(**normalized)
            session.add(doc)
            inserted += 1
        else:
            # Update existing record
            for key, value in normalized.items():
                setattr(existing, key, value)
            updated += 1

    return {"inserted": inserted, "updated": updated, "skipped": skipped}
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
            inserted += 1
            summary["inserted"] += 1
            continue

        changed = False
        for key, value in normalized.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True

        if changed:
            updated += 1
        else:
            skipped += 1

    session.flush()

    return {"inserted": inserted, "updated": updated, "skipped": skipped}


__all__ = ["load_regdocs"]
