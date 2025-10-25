"""FastAPI router exposing the native mobile v2 API surface."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.models.orm import User

from .schemas import (
    BandwidthEstimateResponse,
    BiometricRegistrationRequest,
    BiometricRegistrationResponse,
    BiometricStatusResponse,
    BiometricVerificationRequest,
    BiometricVerificationResponse,
    CameraUploadRequest,
    CameraUploadResponse,
    CacheStatusResponse,
    MobileLoginRequest,
    MobileLoginResponse,
    MobileNearbyKitchensResponse,
    MobileKitchenDetailResponse,
    MobileUpcomingBookingsResponse,
    NotificationRegistrationRequest,
    NotificationRegistrationResponse,
    OfflineSyncResponse,
    OfflineUploadRequest,
    OfflineUploadResponse,
    PerformanceMetricsResponse,
    PerformanceReportRequest,
    PerformanceReportResponse,
    QuickBookingRequest,
    QuickBookingResponse,
    QuickSearchFilters,
    QuickSearchResponse,
)
from .service import MobileGatewayService

router = APIRouter(prefix="/api/v2/mobile", tags=["mobile"])


async def get_mobile_service(
    session: AsyncSession = Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
) -> MobileGatewayService:
    return MobileGatewayService(session, redis)


@router.post("/auth/login", response_model=MobileLoginResponse)
async def mobile_login(
    payload: MobileLoginRequest,
    service: MobileGatewayService = Depends(get_mobile_service),
) -> MobileLoginResponse:
    return await service.login(payload)


@router.get("/kitchens/nearby", response_model=MobileNearbyKitchensResponse)
async def kitchens_nearby(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    radius_km: float = Query(10.0, gt=0.1, le=150.0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> MobileNearbyKitchensResponse:
    return await service.nearby_kitchens(
        current_user,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
    )


@router.get("/bookings/upcoming", response_model=MobileUpcomingBookingsResponse)
async def upcoming_bookings(
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> MobileUpcomingBookingsResponse:
    return await service.upcoming_bookings(current_user)


@router.post("/notifications/register", response_model=NotificationRegistrationResponse)
async def register_notifications(
    payload: NotificationRegistrationRequest,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> NotificationRegistrationResponse:
    return await service.register_push_token(current_user, payload)


@router.get("/data/sync", response_model=OfflineSyncResponse)
async def offline_sync(
    background_interval_minutes: int | None = Query(None, ge=15, le=720),
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> OfflineSyncResponse:
    return await service.sync_offline_data(
        current_user,
        background_interval_minutes=background_interval_minutes,
    )


@router.post("/data/upload", response_model=OfflineUploadResponse)
async def upload_offline_actions(
    payload: OfflineUploadRequest,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> OfflineUploadResponse:
    return await service.upload_offline_actions(current_user, payload)


@router.get("/cache/status", response_model=CacheStatusResponse)
async def cache_status(
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> CacheStatusResponse:
    return await service.cache_status(current_user)


@router.get("/search/quick", response_model=QuickSearchResponse)
async def quick_search(
    query: str | None = Query(None, min_length=1, max_length=120),
    city: str | None = Query(None, min_length=1, max_length=120),
    max_price: float | None = Query(None, gt=0),
    min_trust_score: float | None = Query(None, ge=0, le=5),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> QuickSearchResponse:
    _ = current_user
    filters = QuickSearchFilters(
        query=query,
        city=city,
        max_price=max_price,
        min_trust_score=min_trust_score,
        limit=limit,
    )
    return await service.quick_search(filters)


@router.post("/bookings/quick", response_model=QuickBookingResponse)
async def quick_booking(
    payload: QuickBookingRequest,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> QuickBookingResponse:
    return await service.quick_book(current_user, payload)


@router.get("/kitchens/{kitchen_id}/mobile", response_model=MobileKitchenDetailResponse)
async def kitchen_mobile_view(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> MobileKitchenDetailResponse:
    _ = current_user
    return await service.kitchen_detail(kitchen_id)


@router.post("/camera/upload", response_model=CameraUploadResponse)
async def camera_upload(
    payload: CameraUploadRequest,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> CameraUploadResponse:
    return await service.upload_camera_media(current_user, payload)


@router.post("/auth/biometric/register", response_model=BiometricRegistrationResponse)
async def register_biometric(
    payload: BiometricRegistrationRequest,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> BiometricRegistrationResponse:
    return await service.register_biometric(current_user, payload)


@router.post("/auth/biometric/verify", response_model=BiometricVerificationResponse)
async def verify_biometric(
    payload: BiometricVerificationRequest,
    service: MobileGatewayService = Depends(get_mobile_service),
) -> BiometricVerificationResponse:
    return await service.verify_biometric(payload)


@router.get("/auth/biometric/status", response_model=BiometricStatusResponse)
async def biometric_status(
    device_id: str = Query(..., min_length=3, max_length=255),
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> BiometricStatusResponse:
    return await service.biometric_status(current_user, device_id)


@router.get("/performance/metrics", response_model=PerformanceMetricsResponse)
async def performance_metrics(
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> PerformanceMetricsResponse:
    return await service.performance_metrics(current_user)


@router.post("/performance/report", response_model=PerformanceReportResponse)
async def report_performance(
    payload: PerformanceReportRequest,
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> PerformanceReportResponse:
    return await service.report_performance_issue(current_user, payload)


@router.get("/bandwidth/estimate", response_model=BandwidthEstimateResponse)
async def bandwidth_estimate(
    current_user: User = Depends(get_current_user),
    service: MobileGatewayService = Depends(get_mobile_service),
) -> BandwidthEstimateResponse:
    return await service.bandwidth_estimate(current_user)

