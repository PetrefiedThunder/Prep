"""API surface exposing lightweight host analytics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _as_int(value: Any) -> int:
    """Convert database numeric values to an integer with a safe default."""

    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive conversion guard
        return 0


def _as_isoformat(value: Any) -> str | None:
    """Convert database datetime values to an ISO 8601 string."""

    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


@router.get("/host/{host_id}")
async def get_host_metrics(host_id: UUID, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return host metrics sourced from the ``mv_host_metrics`` view."""

    query = text(
        """
        SELECT host_id,
               total_revenue_cents,
               completed_shifts,
               incident_count,
               calculated_at
        FROM mv_host_metrics
        WHERE host_id = :host_id
        """
    )
    result = await session.execute(query, {"host_id": str(host_id)})
    row = result.mappings().one_or_none()
    data = dict(row) if row else {}

    metrics = {
        "total_revenue_cents": _as_int(data.get("total_revenue_cents")),
        "completed_shifts": _as_int(data.get("completed_shifts")),
        "incident_count": _as_int(data.get("incident_count")),
    }

    return {
        "host_id": str(host_id),
        "data_available": row is not None,
        "metrics": metrics,
        "calculated_at": _as_isoformat(data.get("calculated_at")) if row else None,
    }
