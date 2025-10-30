"""FastAPI router exposing integration health endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from .state import integration_status_store

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.get("/status")
async def get_integration_status() -> dict[str, list[dict[str, object]]]:
    """Return the current snapshot of integration statuses."""

    statuses = await integration_status_store.list_statuses()
    payload = [status.as_frontend_payload() for status in statuses]
    return {"integrations": payload}


__all__ = ["router"]
