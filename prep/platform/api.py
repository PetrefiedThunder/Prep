"""FastAPI router implementing the Prep core platform API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import boto3
from botocore.client import BaseClient
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from docusign_client import DocuSignClient
from prep.api.errors import http_exception
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.platform import schemas
from prep.platform.contracts_service import SubleaseContractService
from prep.platform.service import PlatformError, PlatformService
from prep.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


async def get_platform_service(
    session: AsyncSession = Depends(get_db),
    cache: RedisProtocol = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> PlatformService:
    return PlatformService(session, cache, settings)


def get_docusign_client(
    request: Request, settings: Settings = Depends(get_settings)
) -> DocuSignClient:
    if not settings.docusign_account_id or not settings.docusign_access_token:
        raise http_exception(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="platform.integrations.docusign_missing",
            message="DocuSign credentials are not configured",
        )
    return DocuSignClient(
        base_url=str(settings.docusign_base_url),
        account_id=settings.docusign_account_id,
        access_token=settings.docusign_access_token,
    )


def get_s3_client() -> BaseClient:
    return boto3.client("s3")


async def get_sublease_contract_service(
    session: AsyncSession = Depends(get_db),
    docusign: DocuSignClient = Depends(get_docusign_client),
    s3_client: BaseClient = Depends(get_s3_client),
    settings: Settings = Depends(get_settings),
) -> SubleaseContractService:
    return SubleaseContractService(session, docusign, s3_client, settings)


def _handle_service_error(request: Request, exc: PlatformError):
    raise http_exception(
        request,
        status_code=exc.status_code,
        code=getattr(exc, "code", "platform_error"),
        message=str(exc),
        metadata=getattr(exc, "metadata", None),
    )


def _parse_review_cursor(request: Request, cursor: str | None) -> tuple[datetime, UUID] | None:
    if cursor is None:
        return None
    try:
        timestamp_raw, review_id_raw = cursor.split("::", 1)
        timestamp = datetime.fromisoformat(timestamp_raw)
        review_id = UUID(review_id_raw)
    except (ValueError, AttributeError):
        raise http_exception(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="platform.reviews.invalid_cursor",
            message="Cursor must be formatted as <ISO timestamp>::<review id>",
        )
    return timestamp, review_id


@router.post("/users/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: schemas.UserRegistrationRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.UserResponse:
    try:
        user = await service.register_user(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_user(user)


@router.post("/auth/login", response_model=schemas.AuthenticatedUserResponse)
async def login_user(
    payload: schemas.UserLoginRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.AuthenticatedUserResponse:
    try:
        user, token, expires_at = await service.authenticate_user(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.AuthenticatedUserResponse(
        access_token=token,
        expires_at=expires_at,
        user=schemas.serialize_user(user),
    )


@router.post("/kitchens", response_model=schemas.KitchenResponse, status_code=status.HTTP_201_CREATED)
async def create_kitchen(
    payload: schemas.KitchenCreateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.KitchenResponse:
    try:
        kitchen = await service.create_kitchen(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_kitchen(kitchen)


@router.patch("/kitchens/{kitchen_id}", response_model=schemas.KitchenResponse)
async def update_kitchen(
    kitchen_id: UUID,
    payload: schemas.KitchenUpdateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.KitchenResponse:
    try:
        kitchen = await service.update_kitchen(kitchen_id, payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_kitchen(kitchen)


@router.post("/bookings", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: schemas.BookingCreateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.BookingResponse:
    try:
        booking = await service.create_booking(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_booking(booking)


@router.patch("/bookings/{booking_id}", response_model=schemas.BookingResponse)
async def update_booking(
    booking_id: UUID,
    payload: schemas.BookingStatusUpdateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.BookingResponse:
    try:
        booking = await service.update_booking_status(booking_id, payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_booking(booking)


@router.post("/reviews", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: schemas.ReviewCreateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.ReviewResponse:
    try:
        review = await service.create_review(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_review(review)


@router.get("/reviews/kitchens/{kitchen_id}", response_model=schemas.ReviewListResponse)
async def list_reviews(
    kitchen_id: UUID,
    request: Request,
    cursor: str | None = Query(
        default=None,
        description="Cursor returned by the previous page of results",
    ),
    limit: int = Query(20, ge=1, le=100),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.ReviewListResponse:
    parsed_cursor = _parse_review_cursor(request, cursor)
    try:
        reviews, next_cursor = await service.list_reviews_for_kitchen(
            kitchen_id,
            cursor=parsed_cursor,
            limit=limit,
        )
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.ReviewListResponse(
        items=[schemas.serialize_review(review) for review in reviews],
        pagination=schemas.CursorPageMeta(
            cursor=cursor,
            next_cursor=next_cursor,
            limit=limit,
            has_more=next_cursor is not None,
        ),
    )


@router.post("/payments/intent", response_model=schemas.PaymentIntentResponse)
async def create_payment_intent(
    payload: schemas.PaymentIntentCreateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.PaymentIntentResponse:
    try:
        client_secret = await service.create_payment_intent(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.PaymentIntentResponse(client_secret=client_secret)


@router.post(
    "/contracts/sublease/send",
    response_model=schemas.SubleaseContractSendResponse,
)
async def send_sublease_contract(
    payload: schemas.SubleaseContractSendRequest,
    request: Request,
    service: SubleaseContractService = Depends(get_sublease_contract_service),
) -> schemas.SubleaseContractSendResponse:
    try:
        result = await service.send_contract(
            booking_id=payload.booking_id,
            signer_email=payload.signer_email,
            signer_name=payload.signer_name,
            return_url=payload.return_url,
        )
    except PlatformError as exc:
        _handle_service_error(request, exc)

    return schemas.SubleaseContractSendResponse(
        booking_id=result.contract.booking_id,
        envelope_id=result.contract.envelope_id,
        sign_url=result.signing_url,
    )


@router.get(
    "/contracts/sublease/status/{booking_id}",
    response_model=schemas.SubleaseContractStatusResponse,
)
async def get_sublease_contract_status(
    booking_id: UUID,
    request: Request,
    service: SubleaseContractService = Depends(get_sublease_contract_service),
) -> schemas.SubleaseContractStatusResponse:
    try:
        contract = await service.get_contract_status(booking_id)
    except PlatformError as exc:
        _handle_service_error(request, exc)

    return schemas.SubleaseContractStatusResponse(
        booking_id=contract.booking_id,
        envelope_id=contract.envelope_id,
        status=contract.status,
        sign_url=contract.sign_url,
        document_s3_bucket=contract.document_s3_bucket,
        document_s3_key=contract.document_s3_key,
        completed_at=contract.completed_at,
        last_checked_at=contract.last_checked_at,
    )


@router.post(
    "/compliance", response_model=schemas.ComplianceDocumentResponse, status_code=status.HTTP_201_CREATED
)
async def create_compliance_document(
    payload: schemas.ComplianceDocumentCreateRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.ComplianceDocumentResponse:
    try:
        document = await service.create_compliance_document(payload)
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.serialize_compliance_document(document)


__all__ = ["router"]
