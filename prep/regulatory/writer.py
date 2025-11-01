"""Persistence helpers for city-level regulatory requirements and fee schedules."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prep.models.db import SessionLocal
from prep.regulatory.models import FeeSchedule, RegRequirement


def _json_ready(value: Any) -> Any:
    """Return a JSON-serialisable representation of *value*."""

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}

    if isinstance(value, (set, tuple, list)):
        return [_json_ready(item) for item in value]

    if isinstance(value, UUID):
        return str(value)

    return json.loads(json.dumps(value, default=str))


def _unique_strings(values: Iterable[Any]) -> list[str]:
    """Normalise *values* into a list of unique, non-empty strings."""

    seen: set[str] = set()
    result: list[str] = []
    for raw in values or []:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _normalise_fee_item(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "name" not in payload or "amount_cents" not in payload:
        raise ValueError("Fee items require 'name' and 'amount_cents' fields")

    name = str(payload["name"]).strip()
    if not name:
        raise ValueError("Fee item name cannot be blank")

    try:
        amount_cents = int(payload["amount_cents"])
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("Fee item amount must be an integer") from exc

    item: dict[str, Any] = {
        "name": name,
        "amount_cents": amount_cents,
        "kind": str(payload.get("kind") or "one_time").lower(),
    }

    if payload.get("cadence") is not None:
        item["cadence"] = str(payload["cadence"]).lower()
    if payload.get("unit") is not None:
        item["unit"] = str(payload["unit"]).lower()

    # Normalise optional flags and notes
    if payload.get("incremental") is not None:
        item["incremental"] = bool(payload["incremental"])
    if payload.get("notes") is not None:
        item["notes"] = str(payload["notes"]).strip()

    for key in ("tier_min_inclusive", "tier_max_inclusive"):
        if payload.get(key) is not None:
            try:
                item[key] = int(payload[key])
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ValueError(f"Fee item '{key}' must be numeric") from exc

    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping):
        item["metadata"] = _json_ready(metadata)

    return item


def _normalise_schedule_payload(
    *,
    jurisdiction: str,
    paperwork: Sequence[str] | None,
    fees: Sequence[Mapping[str, Any]] | None,
    notes: str | None,
    source_url: str | None,
    effective_date: datetime | None,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    jurisdiction_norm = str(jurisdiction).strip()
    if not jurisdiction_norm:
        raise ValueError("jurisdiction must be provided")

    paperwork_values = _unique_strings(paperwork or [])
    fee_items = [_normalise_fee_item(item) for item in fees or []]

    canonical = {
        "jurisdiction": jurisdiction_norm,
        "paperwork": paperwork_values,
        "fees": sorted(
            fee_items,
            key=lambda entry: (
                entry.get("name", "").lower(),
                entry.get("kind", ""),
                entry.get("cadence", ""),
                entry.get("unit", ""),
            ),
        ),
    }

    checksum_payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    checksum = hashlib.sha256(checksum_payload).hexdigest()

    schedule: dict[str, Any] = {
        "jurisdiction": jurisdiction_norm,
        "checksum": checksum,
        "paperwork": paperwork_values,
        "fees": fee_items,
        "metadata": _json_ready(metadata) if metadata else {},
    }

    if notes:
        schedule["notes"] = notes.strip()
    if source_url:
        schedule["source_url"] = source_url.strip()
    if effective_date:
        schedule["effective_date"] = effective_date

    return schedule


def _coerce_fee_schedule_id(value: Any) -> str | UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, (UUID, str)):
        return value
    if hasattr(value, "id"):
        return getattr(value, "id")
    return str(value)


def _normalise_requirement_payload(
    jurisdiction: str,
    raw: Mapping[str, Any],
    default_fee_schedule_id: str | UUID | None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError("Requirement payloads must be mapping instances")

    data = dict(raw)

    requirement_id = (
        data.pop("requirement_id", None)
        or data.pop("external_id", None)
        or data.pop("id", None)
    )
    if not requirement_id:
        raise ValueError("Requirement payload missing 'requirement_id'")

    label = (
        data.pop("label", None)
        or data.pop("requirement_label", None)
        or data.pop("title", None)
    )
    if not label:
        raise ValueError("Requirement payload missing 'label'")

    requirement_type = (
        data.pop("requirement_type", None)
        or data.pop("type", None)
        or "general"
    )
    summary = data.pop("summary", None) or data.pop("description", None)

    documents = data.pop("documents", None) or data.pop("required_documents", None) or []
    applies_to = data.pop("applies_to", None) or data.pop("applicable_to", None) or []
    tags = data.pop("tags", [])

    metadata_payload = data.pop("metadata", {})
    if metadata_payload and not isinstance(metadata_payload, Mapping):
        raise TypeError("Requirement 'metadata' must be a mapping if provided")

    fee_schedule_ref = _coerce_fee_schedule_id(
        data.pop("fee_schedule_id", None)
        or data.pop("fee_schedule", None)
        or default_fee_schedule_id
    )

    status = data.pop("status", "active")
    source_url = data.pop("source_url", None) or data.pop("url", None)

    metadata: dict[str, Any] = dict(metadata_payload or {})
    for key, value in data.items():
        if value is not None:
            metadata[str(key)] = _json_ready(value)

    jurisdiction_norm = str(jurisdiction).strip()
    if not jurisdiction_norm:
        raise ValueError("jurisdiction must be provided")

    requirement = {
        "jurisdiction": jurisdiction_norm,
        "external_id": str(requirement_id),
        "label": str(label),
        "requirement_type": str(requirement_type).lower(),
        "summary": summary,
        "documents": _unique_strings(documents),
        "applies_to": _unique_strings(applies_to),
        "tags": _unique_strings(tags),
        "metadata": _json_ready(metadata),
        "status": str(status).lower(),
        "last_seen_at": datetime.utcnow(),
    }

    if source_url:
        requirement["source_url"] = str(source_url)
    if fee_schedule_ref is not None:
        requirement["fee_schedule_id"] = fee_schedule_ref

    return requirement


@contextmanager
def _managed_session(session: Session | None) -> Iterator[Session]:
    if session is not None:
        yield session
        return

    scoped_session = SessionLocal()
    scoped_session.expire_on_commit = False
    try:
        yield scoped_session
        scoped_session.commit()
    except Exception:
        scoped_session.rollback()
        raise
    finally:
        scoped_session.close()


def write_fee_schedule(
    *,
    jurisdiction: str,
    paperwork: Sequence[str] | None = None,
    fees: Sequence[Mapping[str, Any]] | None = None,
    notes: str | None = None,
    source_url: str | None = None,
    effective_date: datetime | None = None,
    metadata: Mapping[str, Any] | None = None,
    session: Session | None = None,
) -> FeeSchedule:
    """Insert or update a :class:`FeeSchedule` for *jurisdiction*."""

    schedule_payload = _normalise_schedule_payload(
        jurisdiction=jurisdiction,
        paperwork=paperwork,
        fees=fees,
        notes=notes,
        source_url=source_url,
        effective_date=effective_date,
        metadata=metadata,
    )

    with _managed_session(session) as active_session:
        existing = active_session.execute(
            select(FeeSchedule).where(FeeSchedule.jurisdiction == schedule_payload["jurisdiction"])
        ).scalar_one_or_none()

        if existing is None:
            record = FeeSchedule(**schedule_payload)
            active_session.add(record)
        else:
            for key, value in schedule_payload.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            record = existing

        active_session.flush()
        return record


def write_reg_requirements(
    *,
    jurisdiction: str,
    requirements: Sequence[Mapping[str, Any]],
    session: Session | None = None,
    fee_schedule_id: str | UUID | None = None,
) -> list[RegRequirement]:
    """Upsert regulatory requirements for *jurisdiction*."""

    if not requirements:
        return []

    records: list[RegRequirement] = []
    payloads = [
        _normalise_requirement_payload(jurisdiction, item, fee_schedule_id)
        for item in requirements
    ]

    with _managed_session(session) as active_session:
        for payload in payloads:
            stmt = select(RegRequirement).where(
                RegRequirement.jurisdiction == payload["jurisdiction"],
                RegRequirement.external_id == payload["external_id"],
            )
            existing = active_session.execute(stmt).scalar_one_or_none()

            if existing is None:
                record = RegRequirement(**payload)
                active_session.add(record)
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                record = existing

            active_session.flush()
            records.append(record)

    return records


__all__ = ["write_fee_schedule", "write_reg_requirements"]
