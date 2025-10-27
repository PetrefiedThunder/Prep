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
            session.add(RegDoc(**normalized))
            inserted += 1
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
