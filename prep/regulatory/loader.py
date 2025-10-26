"""Helpers for persisting regulatory documents."""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from prep.regulatory.models import RegDoc

_REGDOC_FIELDS = {
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


def _normalize_regdoc(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "sha256_hash" not in payload or not payload["sha256_hash"]:
        raise ValueError("RegDoc payload missing required 'sha256_hash'")

    normalized = {
        key: payload[key]
        for key in _REGDOC_FIELDS
        if key in payload and payload[key] is not None
    }
    normalized.setdefault("raw_payload", dict(payload))
    return normalized


def load_regdoc(session: Session, regdocs: list[dict[str, Any]]) -> int:
    """Insert or update :class:`RegDoc` rows based on their SHA-256 hash."""

    if not regdocs:
        return 0

    inserted = 0
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
            for key, value in normalized.items():
                setattr(existing, key, value)

    session.flush()
    return inserted


__all__ = ["load_regdoc"]

