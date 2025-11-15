"""FastAPI router exposing logistics capabilities."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from prep.data_pipeline.cdc import build_cdc_stream
from prep.logistics import schemas
from prep.logistics.onfleet import OnfleetClient
from prep.logistics.service import LogisticsService
from prep.settings import Settings, get_settings

router = APIRouter(prefix="/logistics", tags=["logistics"])


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_logistics_service(
    settings: SettingsDep,
) -> LogisticsService:
    cdc_stream = build_cdc_stream(settings)
    onfleet_client = OnfleetClient(
        base_url=str(settings.onfleet_base_url),
        api_key=settings.onfleet_api_key,
    )
    return LogisticsService(onfleet=onfleet_client, cdc_stream=cdc_stream)


@router.post(
    "/route",
    response_model=schemas.RouteOptimizationResponse,
    status_code=status.HTTP_200_OK,
)
async def optimize_route(
    payload: schemas.RouteOptimizationRequest,
    service: Annotated[LogisticsService, Depends(get_logistics_service)],
) -> schemas.RouteOptimizationResponse:
    try:
        return await service.optimize_route(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


__all__ = ["router"]
