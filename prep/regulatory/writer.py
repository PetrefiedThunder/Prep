"""Persistence helpers for city-level regulatory requirements and fee schedules."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from collections.abc import Iterable, Iterator, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
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
        return value.id
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
        data.pop("requirement_id", None) or data.pop("external_id", None) or data.pop("id", None)
    )
    if not requirement_id:
        raise ValueError("Requirement payload missing 'requirement_id'")

    label = (
        data.pop("label", None) or data.pop("requirement_label", None) or data.pop("title", None)
    )
    if not label:
        raise ValueError("Requirement payload missing 'label'")

    requirement_type = data.pop("requirement_type", None) or data.pop("type", None) or "general"
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
        "last_seen_at": datetime.now(UTC),
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
            existing.updated_at = datetime.now(UTC)
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
        _normalise_requirement_payload(jurisdiction, item, fee_schedule_id) for item in requirements
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
                existing.updated_at = datetime.now(UTC)
                record = existing

            active_session.flush()
            records.append(record)

    return records


__all__ = ["write_fee_schedule", "write_reg_requirements"]
from prep.regulatory.models import FeeSchedule as FeeScheduleModel

_CADENCE_FACTORS: dict[str, int] = {
    "annual": 1,
    "yearly": 1,
    "semi_annual": 2,
    "semiannual": 2,
    "biannual": 2,
    "quarterly": 4,
    "monthly": 12,
    "weekly": 52,
    "daily": 365,
}

_INTERVAL_FACTORS: dict[str, float] = {
    "annual": 1.0,
    "yearly": 1.0,
    "semiannual": 2.0,
    "semi_annual": 2.0,
    "biannual": 2.0,
    "quarterly": 4.0,
    "monthly": 12.0,
    "weekly": 52.0,
    "daily": 365.0,
    "biennial": 0.5,
}


@contextmanager
def _managed_session(session: Session | None):
    if session is not None:
        yield session
        return

    scoped_session = SessionLocal()
    try:
        yield scoped_session
        scoped_session.commit()
    except Exception:
        scoped_session.rollback()
        raise
    finally:
        scoped_session.close()


def _to_mapping(payload: Any) -> MutableMapping[str, Any]:
    if isinstance(payload, MutableMapping):
        return dict(payload)
    if isinstance(payload, Mapping):
        return dict(payload)
    if dataclasses.is_dataclass(payload):
        return dataclasses.asdict(payload)
    if hasattr(payload, "model_dump"):
        return payload.model_dump()  # type: ignore[return-value]
    if hasattr(payload, "dict"):
        return payload.dict()  # type: ignore[return-value]
    if hasattr(payload, "__dict__"):
        return {key: value for key, value in vars(payload).items() if not key.startswith("_")}
    raise TypeError(f"Unsupported payload type: {type(payload)!r}")


def _jsonify(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonify(val) for key, val in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonify(item) for item in value]
    if dataclasses.is_dataclass(value):
        return _jsonify(dataclasses.asdict(value))
    if hasattr(value, "model_dump"):
        return _jsonify(value.model_dump())  # type: ignore[call-arg]
    if hasattr(value, "dict"):
        return _jsonify(value.dict())  # type: ignore[call-arg]
    return str(value)


def _normalise_fee_items(items: Sequence[Any] | None) -> list[dict[str, Any]]:
    if not items:
        return []

    normalised: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, Mapping):
            data = dict(item)
        elif dataclasses.is_dataclass(item):
            data = dataclasses.asdict(item)
        elif hasattr(item, "model_dump"):
            data = item.model_dump()  # type: ignore[assignment]
        elif hasattr(item, "dict"):
            data = item.dict()  # type: ignore[assignment]
        else:
            data = _to_mapping(item)
        normalised.append({key: _jsonify(value) for key, value in data.items()})
    return normalised


def _annualise_dataclass_fee(fee: Mapping[str, Any]) -> int:
    kind = str(fee.get("kind") or "").lower()
    if kind == "one_time":
        return int(fee.get("amount_cents") or 0)
    if kind == "recurring":
        cadence = str(fee.get("cadence") or "annual").lower()
        multiplier = _CADENCE_FACTORS.get(cadence, 1)
        amount = int(fee.get("amount_cents") or 0)
        return amount * multiplier
    return 0


def _annualise_pydantic_fee(fee: Mapping[str, Any]) -> int:
    recurring = fee.get("recurring_cents")
    interval = str(fee.get("recurring_interval") or "").lower()
    if not recurring or not interval:
        return 0
    try:
        cents = int(recurring)
    except (TypeError, ValueError):
        return 0
    factor = _INTERVAL_FACTORS.get(interval, 0)
    return int(round(cents * factor))


def _compute_fee_totals(fees: list[dict[str, Any]]) -> dict[str, int]:
    one_time = 0
    recurring = 0
    incremental = 0

    for fee in fees:
        if "amount_cents" in fee and "kind" in fee:
            kind = str(fee.get("kind") or "").lower()
            if kind == "one_time":
                try:
                    one_time += int(fee.get("amount_cents") or 0)
                except (TypeError, ValueError):
                    continue
            elif kind == "recurring":
                recurring += _annualise_dataclass_fee(fee)
            elif kind == "incremental":
                incremental += 1
        else:
            try:
                one_time += int(fee.get("one_time_cents") or 0)
            except (TypeError, ValueError):
                pass
            recurring += _annualise_pydantic_fee(fee)
            if fee.get("incremental"):
                incremental += 1

    return {
        "one_time_cents": int(one_time),
        "recurring_annualized_cents": int(recurring),
        "incremental_fee_count": int(incremental),
    }


def _normalise_fee_schedule(payload: Any) -> dict[str, Any]:
    data = _to_mapping(payload)

    jurisdiction = data.get("jurisdiction") or data.get("city")
    if not jurisdiction:
        raise ValueError("Fee schedule payload missing 'jurisdiction'")

    version = data.get("version") or data.get("year") or "default"
    paperwork = data.get("paperwork") or data.get("documents") or []
    fees_source = data.get("fees") or data.get("items") or []
    fees = _normalise_fee_items(fees_source)
    totals = _compute_fee_totals(fees)

    recognised = {
        "jurisdiction",
        "city",
        "version",
        "year",
        "paperwork",
        "documents",
        "fees",
        "items",
        "notes",
        "totals",
    }

    extra = {
        key: _jsonify(value)
        for key, value in data.items()
        if key not in recognised and value is not None
    }

    return {
        "jurisdiction": str(jurisdiction),
        "version": str(version),
        "notes": _jsonify(data.get("notes")),
        "paperwork": [str(item) for item in paperwork] if paperwork else [],
        "fees": fees,
        "totals": totals,
        "extra": extra,
    }


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (OverflowError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _coerce_list(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        return [_jsonify(value) for value in values]
    return [_jsonify(values)]


def _coerce_fee_amount(requirement: Mapping[str, Any]) -> int | None:
    if "fee_amount_cents" in requirement:
        try:
            return int(requirement["fee_amount_cents"])
        except (TypeError, ValueError):
            return None
    raw_amount = requirement.get("fee_amount") or requirement.get("fee")
    if raw_amount in (None, ""):
        return None
    try:
        value = float(raw_amount)
    except (TypeError, ValueError):
        return None
    return int(round(value * 100))


def _coerce_uuid(value: Any) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _normalise_requirement(payload: Any) -> dict[str, Any]:
    data = _to_mapping(payload)

    external_id = data.get("external_id") or data.get("requirement_id")
    jurisdiction = data.get("jurisdiction") or data.get("city")
    if not external_id:
        raise ValueError("Requirement payload missing 'requirement_id'")
    if not jurisdiction:
        raise ValueError("Requirement payload missing 'jurisdiction'")

    requirement_type = (
        data.get("requirement_type") or data.get("normalized_type") or data.get("type") or "unknown"
    )
    label = data.get("requirement_label") or data.get("label") or data.get("name")
    if not label:
        raise ValueError("Requirement payload missing 'requirement_label'")

    state = data.get("state_code") or data.get("state")
    country = data.get("country_code") or "US"

    applies_to = _coerce_list(data.get("applies_to") or data.get("applicable_to"))
    required_documents = _coerce_list(data.get("required_documents"))
    rules = data.get("rules") or {}
    if not isinstance(rules, Mapping):
        rules = _jsonify(rules)
    else:
        rules = {str(key): _jsonify(value) for key, value in rules.items()}

    recognised = {
        "external_id",
        "requirement_id",
        "jurisdiction",
        "city",
        "jurisdiction_kind",
        "country_code",
        "state_code",
        "state",
        "requirement_type",
        "normalized_type",
        "type",
        "requirement_label",
        "label",
        "name",
        "governing_agency",
        "agency",
        "agency_type",
        "submission_channel",
        "application_url",
        "apply_url",
        "inspection_required",
        "renewal_frequency",
        "renewal_cycle",
        "applies_to",
        "applicable_to",
        "required_documents",
        "rules",
        "source_url",
        "official_url",
        "last_updated",
        "updated_at",
        "fee_amount_cents",
        "fee_amount",
        "fee",
        "fee_schedule",
        "fee_schedule_reference",
        "fee_schedule_id",
    }

    extra = {
        key: _jsonify(value)
        for key, value in data.items()
        if key not in recognised and value is not None
    }

    fee_schedule_ref = data.get("fee_schedule_reference") or data.get("fee_schedule")

    return {
        "external_id": str(external_id),
        "jurisdiction": str(jurisdiction),
        "jurisdiction_kind": str(data.get("jurisdiction_kind") or "city"),
        "country_code": str(country).upper(),
        "state_code": str(state).upper() if state else None,
        "requirement_type": str(requirement_type),
        "normalized_type": (
            str(data.get("normalized_type")) if data.get("normalized_type") else None
        ),
        "requirement_label": str(label),
        "governing_agency": _jsonify(data.get("governing_agency") or data.get("agency")),
        "agency_type": _jsonify(data.get("agency_type")),
        "submission_channel": _jsonify(data.get("submission_channel")),
        "application_url": _jsonify(data.get("application_url") or data.get("apply_url")),
        "inspection_required": _coerce_bool(data.get("inspection_required")),
        "renewal_frequency": _jsonify(data.get("renewal_frequency") or data.get("renewal_cycle")),
        "applies_to": applies_to,
        "required_documents": required_documents,
        "rules": rules if isinstance(rules, Mapping) else {},
        "source_url": _jsonify(data.get("source_url") or data.get("official_url")),
        "last_updated": _parse_datetime(data.get("last_updated") or data.get("updated_at")),
        "fee_schedule_reference": _jsonify(fee_schedule_ref),
        "fee_amount_cents": _coerce_fee_amount(data),
        "fee_schedule_id": _coerce_uuid(data.get("fee_schedule_id")),
        "extra": extra,
    }


def _apply_changes(model: Any, values: Mapping[str, Any]) -> bool:
    changed = False
    for key, value in values.items():
        if key == "id":
            continue
        if getattr(model, key) != value:
            setattr(model, key, value)
            changed = True
    return changed


def write_fee_schedule(
    schedule: Any,
    *,
    session: Session | None = None,
) -> FeeScheduleModel:
    """Insert or update a regulatory fee schedule."""

    payload = _normalise_fee_schedule(schedule)

    with _managed_session(session) as active_session:
        existing = active_session.execute(
            select(FeeScheduleModel)
            .where(FeeScheduleModel.jurisdiction == payload["jurisdiction"])
            .where(FeeScheduleModel.version == payload["version"])
        ).scalar_one_or_none()

        if existing is None:
            record = FeeScheduleModel(**payload)
            active_session.add(record)
            active_session.flush()
            return record

        _apply_changes(existing, payload)
        active_session.flush()
        return existing


def write_reg_requirement(
    requirement: Any,
    *,
    session: Session | None = None,
) -> RegRequirement:
    """Persist a single regulatory requirement."""

    payload = _normalise_requirement(requirement)

    with _managed_session(session) as active_session:
        existing = active_session.execute(
            select(RegRequirement).where(RegRequirement.external_id == payload["external_id"])
        ).scalar_one_or_none()

        if existing is None:
            record = RegRequirement(**payload)
            active_session.add(record)
            active_session.flush()
            return record

        _apply_changes(existing, payload)
        active_session.flush()
        return existing


def write_reg_requirements(
    requirements: Iterable[Any],
    *,
    session: Session | None = None,
) -> dict[str, int]:
    """Persist a batch of regulatory requirements."""

    inserted = 0
    updated = 0

    with _managed_session(session) as active_session:
        for item in requirements:
            payload = _normalise_requirement(item)
            existing = active_session.execute(
                select(RegRequirement).where(RegRequirement.external_id == payload["external_id"])
            ).scalar_one_or_none()

            if existing is None:
                active_session.add(RegRequirement(**payload))
                inserted += 1
                continue

            if _apply_changes(existing, payload):
                updated += 1

        active_session.flush()

    return {"inserted": inserted, "updated": updated}


__all__ = [
    "write_fee_schedule",
    "write_reg_requirement",
    "write_reg_requirements",
]
