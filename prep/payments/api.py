"""FastAPI router for payments integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from prep.api.errors import http_error
from prep.api.errors import http_exception
from prep.database import get_db
from prep.settings import Settings, get_settings

from .schemas import PaymentsConnectRequest, PaymentsConnectResponse
from .service import PaymentsError, PaymentsService

router = APIRouter(prefix="/payments", tags=["payments"])


async def get_payments_service(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PaymentsService:
    """Dependency that provisions the payments service."""

    return PaymentsService(session, settings)


def _handle_payments_error(request: Request, exc: PaymentsError) -> None:
    raise http_exception(
        request,
        status_code=exc.status_code,
        code=getattr(exc, "code", "payments_error"),
        message=str(exc),
        metadata=getattr(exc, "metadata", None),
    )


@router.post("/connect", response_model=PaymentsConnectResponse, status_code=status.HTTP_201_CREATED)
async def connect_stripe_account(
    payload: PaymentsConnectRequest,
    request: Request,
    service: PaymentsService = Depends(get_payments_service),
) -> PaymentsConnectResponse:
    """Create a Stripe Connect account and return the onboarding link."""

    try:
        account_id, onboarding_url = await service.create_connect_account(user_id=payload.user_id)
    except PaymentsError as exc:
        raise http_error(
            request,
            status_code=exc.status_code,
            code="payments.error",
            message=str(exc),
        ) from exc
        _handle_payments_error(request, exc)
    return PaymentsConnectResponse(account_id=account_id, onboarding_url=onboarding_url)


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def handle_webhook(
    request: Request,
    service: PaymentsService = Depends(get_payments_service),
) -> Response:
    """Handle incoming Stripe webhook calls."""

    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        await service.process_webhook(payload, signature)
    except PaymentsError as exc:
        raise http_error(
            request,
            status_code=exc.status_code,
            code="payments.webhook_error",
            message=str(exc),
        ) from exc
        _handle_payments_error(request, exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
