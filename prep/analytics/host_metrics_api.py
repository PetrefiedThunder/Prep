"""API surface exposing lightweight host analytics endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _as_float(value: Any) -> float:
    """Convert database numeric values to a JSON-serializable float."""

    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive conversion guard
        return 0.0


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


@router.get("/host/{host_id}")
async def get_host_metrics(host_id: UUID, session: AsyncSession = Depends(get_db)) -> dict[str, float | int]:
    """Return host metrics sourced from the ``mv_host_metrics`` view."""

    query = text(
        """
        SELECT revenue_last_30, shifts_30, incident_rate
        FROM mv_host_metrics
        WHERE host_id = :host_id
        """
    )
    result = await session.execute(query, {"host_id": str(host_id)})
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host metrics not found for {host_id}",
        )

    data = dict(row)

    return {
        "revenue_last_30": _as_float(data.get("revenue_last_30")),
        "shifts_30": _as_int(data.get("shifts_30")),
        "incident_rate": _as_float(data.get("incident_rate")),
    }
