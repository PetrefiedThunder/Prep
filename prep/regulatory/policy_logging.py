"""Utilities for persisting Open Policy Agent evaluation telemetry."""

from __future__ import annotations

import hashlib
import json
import logging
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from prep.models.db import SessionLocal
from prep.regulatory.models import PolicyDecision

LOGGER = logging.getLogger(__name__)

_MAX_RATIONALE_LENGTH = 1024
_MAX_ERROR_LENGTH = 1024


def _serialise_payload(payload: Any) -> Any:
    """Return a JSON-compatible representation of *payload*."""

    if payload is None:
        return None

    if isinstance(payload, dict):
        return {key: _serialise_payload(value) for key, value in payload.items()}

    if isinstance(payload, (list, tuple, set)):
        return [_serialise_payload(value) for value in payload]

    if isinstance(payload, UUID):
        return str(payload)

    if hasattr(payload, "model_dump"):
        return payload.model_dump()

    if is_dataclass(payload):
        return asdict(payload)

    if isinstance(payload, (str, int, float, bool)):
        return payload

    if isinstance(payload, bytes):
        return payload.decode("utf-8", errors="replace")

    return json.loads(json.dumps(payload, default=str))


def _hash_input(payload: Mapping[str, Any] | Any) -> str:
    """Generate a deterministic hash for the supplied policy input payload."""

    canonical = _serialise_payload(payload) or {}
    dump = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()


def _trim(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[:limit]


@contextmanager
def _managed_session(session: Session | None):
    """Yield a SQLAlchemy session, creating one when necessary."""

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


def write_policy_decision(
    *,
    region: str,
    jurisdiction: str,
    package_path: str,
    decision: str,
    input_payload: Mapping[str, Any] | Any,
    duration_ns: int,
    session: Session | None = None,
    rationale: str | None = None,
    error: str | None = None,
    result_payload: Mapping[str, Any] | Any | None = None,
    triggered_by: str | None = None,
    trace_id: str | None = None,
    request_id: str | None = None,
) -> PolicyDecision:
    """Persist a policy decision record using the shared session factory."""

    payload = _serialise_payload(input_payload) or {}
    result = _serialise_payload(result_payload) if result_payload is not None else None
    request_hash = _hash_input(payload)
    duration_ms = max(0, round(duration_ns / 1_000_000))

    with _managed_session(session) as active_session:
        record = PolicyDecision(
            region=region,
            jurisdiction=jurisdiction,
            package_path=package_path,
            decision=decision,
            request_hash=request_hash,
            rationale=_trim(rationale, _MAX_RATIONALE_LENGTH),
            error=_trim(error, _MAX_ERROR_LENGTH),
            duration_ms=duration_ms,
            input_payload=payload,
            result_payload=result,
            triggered_by=triggered_by,
            trace_id=trace_id,
            request_id=request_id,
        )
        active_session.add(record)
        active_session.flush()
        LOGGER.debug(
            "Recorded policy decision", extra={"policy_decision_id": str(record.id)}
        )
        return record


__all__ = ["_hash_input", "write_policy_decision"]
