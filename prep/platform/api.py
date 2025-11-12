"""FastAPI router implementing the Prep core platform API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import boto3
from botocore.client import BaseClient
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from docusign_client import DocuSignClient
from prep.api.errors import http_error, http_exception
from prep.auth import get_current_admin, get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.models.orm import User
from prep.platform import schemas
from prep.platform.contracts_service import SubleaseContractService
from prep.platform.service import PlatformError, PlatformService
from prep.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def get_platform_service(
    session: AsyncSession = Depends(get_db),
    cache: RedisProtocol = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> PlatformService:
    return PlatformService(session, cache, settings)


def _extract_request_metadata(request: Request) -> tuple[str | None, str | None, str | None]:
    client_ip = request.client.host if request.client else None
    device_id = request.headers.get("X-Device-Id")
    user_agent = request.headers.get("User-Agent")
    return device_id, client_ip, user_agent


def get_docusign_client(settings: Settings = Depends(get_settings)) -> DocuSignClient:
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
    raise http_error(
        request,
        status_code=exc.status_code,
        code="platform.error",
        message=str(exc),
    )
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


@router.post(
    "/users/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED
)
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
        user, token, refresh_token, expires_at = await service.authenticate_user(payload)
        device_id, client_ip, user_agent = _extract_request_metadata(request)
        user, token, expires_at, refresh_token, refresh_expires = await service.authenticate_user(
            payload,
            device_fingerprint=device_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except PlatformError as exc:
        _handle_service_error(request, exc)
    return schemas.AuthenticatedUserResponse(
        access_token=token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        refresh_expires_at=refresh_expires,
        user=schemas.serialize_user(user),
    )


@router.post("/auth/token", response_model=schemas.TokenPairResponse)
async def issue_access_token(
    payload: schemas.UserLoginRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.TokenPairResponse:
    try:
        _, token, refresh_token, expires_at = await service.authenticate_user(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.TokenPairResponse(
        access_token=token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


@router.post("/auth/refresh", response_model=schemas.TokenPairResponse)
async def refresh_access_token(
    payload: schemas.RefreshTokenRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.TokenPairResponse:
    try:
        _, token, refresh_token, expires_at = await service.refresh_access_token(
            payload.refresh_token
        )
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.TokenPairResponse(
        access_token=token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


@router.post(
    "/auth/api-keys",
    response_model=schemas.APIKeyWithSecretResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    payload: schemas.APIKeyCreateRequest,
    current_user=Depends(get_current_user),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.APIKeyWithSecretResponse:
    try:
        api_key, secret = await service.create_api_key(current_user.id, payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    serialized = schemas.serialize_api_key(api_key)
    return schemas.APIKeyWithSecretResponse(**serialized.model_dump(), secret=secret)


@router.post(
    "/auth/api-keys/{key_id}/rotate",
    response_model=schemas.APIKeyWithSecretResponse,
)
async def rotate_api_key(
    key_id: UUID,
    current_user=Depends(get_current_user),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.APIKeyWithSecretResponse:
    try:
        api_key, secret = await service.rotate_api_key(current_user.id, key_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    serialized = schemas.serialize_api_key(api_key)
    return schemas.APIKeyWithSecretResponse(**serialized.model_dump(), secret=secret)


@auth_router.post("/token", response_model=schemas.TokenPairResponse)
async def issue_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.TokenPairResponse:
    login_payload = schemas.UserLoginRequest(
        email=form_data.username,
        password=form_data.password,
    )
    try:
        device_id, client_ip, user_agent = _extract_request_metadata(request)
        _, token, expires_at, refresh_token, refresh_expires = await service.authenticate_user(
            login_payload,
            device_fingerprint=device_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except PlatformError as exc:
        raise _handle_service_error(exc)

    return schemas.TokenPairResponse(
        access_token=token,
        expires_at=expires_at,
        refresh_token=refresh_token,
        refresh_expires_at=refresh_expires,
    )


@auth_router.post("/refresh", response_model=schemas.TokenPairResponse)
async def refresh_access_token(
    payload: schemas.RefreshTokenRequest,
    request: Request,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.TokenPairResponse:
    try:
        device_id, client_ip, user_agent = _extract_request_metadata(request)
        _, token, expires_at, new_refresh, refresh_expires = await service.refresh_access_token(
            payload.refresh_token,
            device_fingerprint=payload.device_fingerprint or device_id,
            ip_address=payload.ip_address or client_ip,
            user_agent=payload.user_agent or user_agent,
        )
    except PlatformError as exc:
        raise _handle_service_error(exc)

    return schemas.TokenPairResponse(
        access_token=token,
        expires_at=expires_at,
        refresh_token=new_refresh,
        refresh_expires_at=refresh_expires,
    )


@auth_router.post(
    "/api-keys",
    response_model=schemas.APIKeyIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_api_key(
    payload: schemas.APIKeyIssueRequest,
    current_user: User = Depends(get_current_admin),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.APIKeyIssueResponse:
    try:
        api_key, secret = await service.issue_api_key(current_user.id, payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_api_key_issue(api_key, secret)


@auth_router.post(
    "/api-keys/{api_key_id}/rotate",
    response_model=schemas.APIKeyIssueResponse,
)
async def rotate_api_key(
    api_key_id: UUID,
    payload: schemas.APIKeyRotateRequest | None = None,
    current_user: User = Depends(get_current_admin),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.APIKeyIssueResponse:
    try:
        expires = payload.expires_in_days if payload else None
        api_key, secret = await service.rotate_api_key(
            api_key_id,
            actor_id=current_user.id,
            expires_in_days=expires,
        )
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_api_key_issue(api_key, secret)


@auth_router.post(
    "/api-keys/{api_key_id}/revoke",
    response_model=schemas.APIKeyResponse,
)
async def revoke_api_key(
    api_key_id: UUID,
    current_user: User = Depends(get_current_admin),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.APIKeyResponse:
    try:
        api_key = await service.revoke_api_key(api_key_id, actor_id=current_user.id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_api_key(api_key)


@router.post(
    "/kitchens", response_model=schemas.KitchenResponse, status_code=status.HTTP_201_CREATED
)
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


@router.post(
    "/bookings", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED
)
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


@router.get(
    "/reviews/kitchens/{kitchen_id}",
    response_model=schemas.ReviewCollectionResponse,
)
async def list_reviews(
    kitchen_id: UUID,
    request: Request,
    cursor: datetime | None = Query(default=None, description="Cursor from a previous page"),
    limit: int = Query(20, ge=1, le=100),
    service: PlatformService = Depends(get_platform_service),
) -> schemas.ReviewCollectionResponse:
    try:
        reviews, next_cursor, total = await service.list_reviews_for_kitchen(
            kitchen_id=kitchen_id,
            cursor=cursor,
            limit=limit,
        )
    except PlatformError as exc:
        _handle_service_error(request, exc)
    items = [schemas.serialize_review(review) for review in reviews]
    return schemas.ReviewCollectionResponse(
        items=items,
        pagination=schemas.CursorPagination(
            limit=limit,
            cursor=cursor,
            next_cursor=next_cursor,
            total=total,
        ),
    )


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


@router.post(
    "/documents", response_model=schemas.DocumentUploadResponse, status_code=status.HTTP_201_CREATED
)
async def create_document_upload(
    payload: schemas.DocumentUploadCreateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.DocumentUploadResponse:
    try:
        document = await service.create_document_upload(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_document_upload(document)


@router.get("/permits/{permit_id}", response_model=schemas.PermitResponse)
async def get_permit(
    permit_id: UUID,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.PermitResponse:
    try:
        permit = await service.get_permit(permit_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_permit(permit)


@router.get(
    "/business/{business_id}/readiness",
    response_model=schemas.BusinessReadinessResponse,
)
async def get_business_readiness(
    business_id: UUID,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.BusinessReadinessResponse:
    try:
        readiness = await service.get_business_readiness(business_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return readiness


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
    "/documents",
    response_model=schemas.DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_upload(
    payload: schemas.DocumentUploadRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.DocumentUploadResponse:
    try:
        document = await service.create_document_upload(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_document_upload(document)


@router.get("/documents/{document_id}", response_model=schemas.DocumentUploadResponse)
async def get_document_upload(
    document_id: UUID,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.DocumentUploadResponse:
    try:
        document = await service.get_document_upload(document_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_document_upload(document)


@router.get("/permits/{permit_id}", response_model=schemas.PermitResponse)
async def get_permit(
    permit_id: UUID,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.PermitResponse:
    try:
        permit = await service.get_permit(permit_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_permit(permit)


@router.get(
    "/business/{business_id}/readiness",
    response_model=schemas.BusinessReadinessResponse,
)
async def get_business_readiness(
    business_id: UUID,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.BusinessReadinessResponse:
    try:
        readiness = await service.get_business_readiness(business_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return readiness


@router.post(
    "/payments/checkout",
    response_model=schemas.CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    payload: schemas.CheckoutRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.CheckoutResponse:
    try:
        record, client_secret = await service.create_checkout(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.CheckoutResponse(
        payment_id=record.id,
        status=record.status,
        total_amount_cents=record.amount_cents,
        currency=record.currency,
        client_secret=client_secret,
        receipt_url=record.receipt_url,
        refunded_amount_cents=record.refunded_amount_cents,
    )


@router.post(
    "/payments/checkout-payment",
    response_model=schemas.CheckoutPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout_payment(
    payload: schemas.CheckoutPaymentCreateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.CheckoutPaymentResponse:
    try:
        payment = await service.create_checkout_payment(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_checkout_payment(payment)


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
    "/compliance",
    response_model=schemas.ComplianceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
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


__all__ = ["router", "auth_router"]
