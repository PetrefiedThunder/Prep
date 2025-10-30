"""FastAPI router exposing POS analytics and webhook endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol, get_redis
from prep.database import get_db

from .analytics import POSAnalyticsService
from .models import POSAnalyticsResponse
from .repository import POSIntegrationRepository
from .toast import ToastAPIError, ToastWebhookProcessor

router = APIRouter(prefix="/api/v1", tags=["pos"])


async def _get_service(
    session: AsyncSession = Depends(get_db),
    cache: RedisProtocol = Depends(get_redis),
) -> POSAnalyticsService:
    return POSAnalyticsService(session, cache)


def _normalize_window(
    *,
    start: datetime | None,
    end: datetime | None,
    hours: int,
) -> tuple[datetime, datetime]:
    if hours <= 0:
        raise HTTPException(status_code=400, detail="hours must be greater than zero")
    now = datetime.now(UTC)
    end_dt = end or now
    start_dt = start or end_dt - timedelta(hours=hours)
    start_utc = start_dt if start_dt.tzinfo else start_dt.replace(tzinfo=UTC)
    end_utc = end_dt if end_dt.tzinfo else end_dt.replace(tzinfo=UTC)
    if end_utc <= start_utc:
        raise HTTPException(status_code=400, detail="end must be after start")
    return start_utc, end_utc


@router.get("/analytics/pos", response_model=POSAnalyticsResponse)
async def get_pos_analytics(
    kitchen_id: UUID | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    service: POSAnalyticsService = Depends(_get_service),
) -> Any:
    window_start, window_end = _normalize_window(start=start, end=end, hours=hours)
    return await service.compute_metrics(kitchen_id=kitchen_id, start=window_start, end=window_end)


@router.post(
    "/webhooks/pos/toast/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def handle_toast_webhook(
    integration_id: UUID,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_db),
) -> Response:
    repository = POSIntegrationRepository(session)
    integration = await repository.get_integration_by_id(integration_id)
    if integration is None or integration.provider.lower() != "toast":
        raise HTTPException(status_code=404, detail="POS integration not found")
    processor = ToastWebhookProcessor()
    try:
        event = processor.normalize_order(payload)
    except ToastAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await repository.upsert_order(integration, event)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
