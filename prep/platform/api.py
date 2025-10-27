"""FastAPI router implementing the Prep core platform API."""

from __future__ import annotations

from uuid import UUID

import boto3
from botocore.client import BaseClient
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from docusign_client import DocuSignClient
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


def get_docusign_client(settings: Settings = Depends(get_settings)) -> DocuSignClient:
    if not settings.docusign_account_id or not settings.docusign_access_token:
        raise HTTPException(status_code=500, detail="DocuSign credentials are not configured")
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


def _handle_service_error(exc: PlatformError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/users/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: schemas.UserRegistrationRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.UserResponse:
    try:
        user = await service.register_user(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_user(user)


@router.post("/auth/login", response_model=schemas.AuthenticatedUserResponse)
async def login_user(
    payload: schemas.UserLoginRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.AuthenticatedUserResponse:
    try:
        user, token, expires_at = await service.authenticate_user(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.AuthenticatedUserResponse(
        access_token=token,
        expires_at=expires_at,
        user=schemas.serialize_user(user),
    )


@router.post("/kitchens", response_model=schemas.KitchenResponse, status_code=status.HTTP_201_CREATED)
async def create_kitchen(
    payload: schemas.KitchenCreateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.KitchenResponse:
    try:
        kitchen = await service.create_kitchen(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_kitchen(kitchen)


@router.patch("/kitchens/{kitchen_id}", response_model=schemas.KitchenResponse)
async def update_kitchen(
    kitchen_id: UUID,
    payload: schemas.KitchenUpdateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.KitchenResponse:
    try:
        kitchen = await service.update_kitchen(kitchen_id, payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_kitchen(kitchen)


@router.post("/bookings", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: schemas.BookingCreateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.BookingResponse:
    try:
        booking = await service.create_booking(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_booking(booking)


@router.patch("/bookings/{booking_id}", response_model=schemas.BookingResponse)
async def update_booking(
    booking_id: UUID,
    payload: schemas.BookingStatusUpdateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.BookingResponse:
    try:
        booking = await service.update_booking_status(booking_id, payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_booking(booking)


@router.post("/reviews", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: schemas.ReviewCreateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.ReviewResponse:
    try:
        review = await service.create_review(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_review(review)


@router.get("/reviews/kitchens/{kitchen_id}", response_model=list[schemas.ReviewResponse])
async def list_reviews(
    kitchen_id: UUID,
    service: PlatformService = Depends(get_platform_service),
) -> list[schemas.ReviewResponse]:
    try:
        reviews = await service.list_reviews_for_kitchen(kitchen_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return [schemas.serialize_review(review) for review in reviews]


@router.post("/payments/intent", response_model=schemas.PaymentIntentResponse)
async def create_payment_intent(
    payload: schemas.PaymentIntentCreateRequest,
    service: PlatformService = Depends(get_platform_service),
) -> schemas.PaymentIntentResponse:
    try:
        client_secret = await service.create_payment_intent(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.PaymentIntentResponse(client_secret=client_secret)


@router.post(
    "/contracts/sublease/send",
    response_model=schemas.SubleaseContractSendResponse,
)
async def send_sublease_contract(
    payload: schemas.SubleaseContractSendRequest,
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
        raise _handle_service_error(exc)

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
    service: SubleaseContractService = Depends(get_sublease_contract_service),
) -> schemas.SubleaseContractStatusResponse:
    try:
        contract = await service.get_contract_status(booking_id)
    except PlatformError as exc:
        raise _handle_service_error(exc)

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
    service: PlatformService = Depends(get_platform_service),
) -> schemas.ComplianceDocumentResponse:
    try:
        document = await service.create_compliance_document(payload)
    except PlatformError as exc:
        raise _handle_service_error(exc)
    return schemas.serialize_compliance_document(document)


__all__ = ["router"]
