"""FastAPI handlers for Square KDS webhook callbacks."""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.scheduling.service import SchedulingService
from integrations.square.webhooks import (
    SquareWebhookVerificationError,
    SquareWebhookVerifier,
    acknowledge_payload,
    parse_prep_time_update,
)

router = APIRouter(prefix="/api/webhooks/square-kds", tags=["webhooks"])


_scheduling_service = SchedulingService()


def get_scheduling_service() -> SchedulingService:
    """Dependency hook for swapping the scheduling service in tests."""

    return _scheduling_service


def get_verifier(request: Request) -> SquareWebhookVerifier:
    """Instantiate a verifier using environment configuration."""

    signature_key = os.getenv("SQUARE_KDS_SIGNATURE_KEY", "")
    notification_url = os.getenv("SQUARE_KDS_NOTIFICATION_URL", str(request.url))
    try:
        return SquareWebhookVerifier(
            signature_key=signature_key, notification_url=notification_url
        )
    except ValueError as exc:  # pragma: no cover - env misconfiguration
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.post("/prep-time")
async def handle_prep_time(
    request: Request,
    service: SchedulingService = Depends(get_scheduling_service),
    verifier: SquareWebhookVerifier = Depends(get_verifier),
) -> dict[str, Any]:
    """Receive Square prep-time updates and forward them to scheduling."""

    body = await request.body()
    signature = request.headers.get("x-square-signature")

    try:
        verifier.verify(body, signature)
    except SquareWebhookVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    try:
        update = parse_prep_time_update(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    window = service.ingest_prep_time_update(update)

    response: dict[str, Any] = dict(acknowledge_payload())
    response.update(
        {
            "order_id": update.order_id,
            "location_id": update.location_id,
            "prep_time_seconds": update.prep_time_seconds,
            "window": {
                "start_at": window.start_at.isoformat(),
                "end_at": window.end_at.isoformat(),
            },
        }
    )
    return response


__all__ = ["router", "get_scheduling_service", "get_verifier"]
