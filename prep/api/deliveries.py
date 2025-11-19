"""FastAPI router exposing delivery integration endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import User, get_current_user
from prep.database import get_db
from prep.delivery import DeliveryService, DeliveryServiceError
from prep.delivery.schemas import (
    DeliveryCreateRequest,
    DeliveryCreateResponse,
    DeliveryStatusUpdate,
)
from prep.settings import Settings, get_settings

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


SessionDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def _get_service(session: SessionDep, settings: SettingsDep) -> DeliveryService:
    return DeliveryService(session, settings)


@router.post("/create", response_model=DeliveryCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    payload: DeliveryCreateRequest,
    current_user: User = Depends(get_current_user),
    service: Annotated[DeliveryService, Depends(_get_service)],
) -> DeliveryCreateResponse:
    """Create a delivery with the specified provider."""

    _ = current_user  # Authentication already enforced

    try:
        return await service.create_delivery(payload)
    except DeliveryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/status", status_code=status.HTTP_202_ACCEPTED)
async def deliveries_status_webhook(
    payload: DeliveryStatusUpdate,
    request: Request,
    service: Annotated[DeliveryService, Depends(_get_service)],
    doordash_signature: str | None = Header(default=None, alias="X-DoorDash-Signature"),
) -> dict[str, str]:
    """Accept status callbacks from delivery providers."""

    raw_body = await request.body()
    if payload.provider.value == "doordash":
        try:
            service.verify_doordash_signature(raw_body, doordash_signature)
        except DeliveryServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        await service.ingest_status_update(payload)
    except DeliveryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return {"status": "accepted"}


__all__ = ["router"]
