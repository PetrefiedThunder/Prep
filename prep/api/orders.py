"""Unified orders endpoint combining delivery providers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import User, require_admin_role
from prep.database import get_db
from prep.delivery import DeliveryService, DeliveryServiceError
from prep.delivery.schemas import OrdersResponse
from prep.settings import Settings, get_settings

router = APIRouter(prefix="/orders", tags=["orders"])


async def _get_service(
    session: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)
) -> DeliveryService:
    return DeliveryService(session, settings)


@router.get("", response_model=OrdersResponse)
async def list_orders(
    current_admin: User = Depends(require_admin_role),
    service: DeliveryService = Depends(_get_service),
) -> OrdersResponse:
    """Return the current state of all third-party deliveries (admin only)."""

    _ = current_admin  # Authentication already enforced

    try:
        return await service.list_orders()
    except DeliveryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


__all__ = ["router"]
