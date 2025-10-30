"""Monitoring endpoints consumed by Grafana dashboards."""

from __future__ import annotations

from fastapi import APIRouter

from prep.integrations.state import integration_status_store

router = APIRouter(tags=["monitoring"])


@router.get("/health/integrations")
async def integrations_health() -> dict[str, object]:
    """Expose aggregated integration metrics."""

    snapshot = await integration_status_store.health_snapshot()
    return snapshot.model_dump(by_alias=True)


__all__ = ["router"]
