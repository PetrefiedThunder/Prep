"""FastAPI router implementing the Prep core platform API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.platform import schemas
from prep.platform.service import PlatformError, PlatformService
from prep.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


async def get_platform_service(
    session: AsyncSession = Depends(get_db),
    cache: RedisProtocol = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> PlatformService:
    return PlatformService(session, cache, settings)


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
