"""Event emission stubs for ingestion outputs."""
from __future__ import annotations

from typing import Any

from .normalize import NormalizedDoc


def emit_raw(doc: NormalizedDoc) -> None:
    """Emit a raw normalized document to the reg.raw topic."""

    raise NotImplementedError("Kafka integration not implemented")


def emit_diff(doc_id: str, changes: list[dict[str, Any]]) -> None:
    """Emit a diff payload to the reg.diff topic."""

    raise NotImplementedError("Kafka integration not implemented")
