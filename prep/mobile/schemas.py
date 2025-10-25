"""Pydantic schemas powering the native mobile API foundation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """Metadata describing the mobile device."""

    device_id: str = Field(min_length=3, max_length=255)
    platform: Literal["ios", "android", "web", "other"]
    app_version: str | None = Field(default=None, max_length=32)
    os_version: str | None = Field(default=None, max_length=32)


class MobileAuthTokens(BaseModel):
    """Bearer token bundle issued to the mobile client."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires")


class MobileLoginRequest(BaseModel):
    """Request payload for mobile optimized authentication."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=255)
    device: DeviceInfo


class MobileLoginResponse(BaseModel):
    """Successful login response returning issued tokens and feature flags."""

    user_id: UUID
    tokens: MobileAuthTokens
    features: list[str]
    background_sync_interval_minutes: int | None = None


class MobileKitchenSummary(BaseModel):
    """Summarized kitchen information for list responses."""

    kitchen_id: UUID
    name: str
    distance_km: float | None
    city: str | None
    state: str | None
    hourly_rate: float | None
    trust_score: float | None
    normalized_rating: float | None
    rating_count: int

    model_config = {"from_attributes": True}


class MobileNearbyKitchensResponse(BaseModel):
    """Nearby kitchen discovery response."""

    items: list[MobileKitchenSummary]
    cached: bool
    generated_at: datetime


class MobileBookingSummary(BaseModel):
    """Upcoming booking details for dashboard view."""

    booking_id: UUID
    kitchen_id: UUID
    kitchen_name: str
    status: str
    start_time: datetime
    end_time: datetime
    role: Literal["host", "customer"]


class MobileUpcomingBookingsResponse(BaseModel):
    """Response envelope for upcoming bookings."""

    items: list[MobileBookingSummary]
    generated_at: datetime


class NotificationRegistrationRequest(BaseModel):
    """Push notification registration payload."""

    device: DeviceInfo
    push_token: str = Field(min_length=10, max_length=512)
    locale: str | None = Field(default=None, max_length=16)


class NotificationRegistrationResponse(BaseModel):
    """Acknowledgement of push notification registration."""

    registered: bool
    expires_at: datetime


class OfflineAction(BaseModel):
    """Offline action queued for upload once connectivity is restored."""

    action_type: str = Field(description="Domain specific action identifier")
    payload: dict = Field(default_factory=dict)
    recorded_at: datetime


class OfflineSyncResponse(BaseModel):
    """Payload returned to hydrate the offline cache."""

    user_id: UUID
    kitchens: list[MobileKitchenSummary]
    bookings: list[MobileBookingSummary]
    preferences: dict
    generated_at: datetime
    next_background_sync: datetime | None = None


class OfflineUploadRequest(BaseModel):
    """Uploaded offline interactions for reconciliation."""

    actions: list[OfflineAction]


class OfflineUploadResponse(BaseModel):
    """Summary of processed offline actions."""

    processed: int
    queued: int
    next_sync_hint_minutes: int


class CacheStatusResponse(BaseModel):
    """High level status of cached mobile data for the user."""

    has_sync_snapshot: bool
    last_synced_at: datetime | None
    pending_actions: int
    background_interval_minutes: int | None


class QuickSearchFilters(BaseModel):
    """Optional filters for quick mobile search."""

    query: str | None = None
    city: str | None = None
    max_price: float | None = None
    min_trust_score: float | None = None
    limit: int = Field(default=10, ge=1, le=50)


class QuickSearchResponse(BaseModel):
    """Quick search results optimized for mobile."""

    items: list[MobileKitchenSummary]
    generated_at: datetime


class QuickBookingRequest(BaseModel):
    """Single shot booking creation payload."""

    kitchen_id: UUID
    start_time: datetime
    end_time: datetime
    guests: int = Field(default=1, ge=1, le=200)
    notes: str | None = Field(default=None, max_length=500)


class QuickBookingResponse(BaseModel):
    """Response for one-tap booking creation."""

    booking: MobileBookingSummary
    created: bool


class MobileKitchenDetailResponse(BaseModel):
    """Detailed kitchen view tailored for native clients."""

    kitchen: MobileKitchenSummary
    description: str | None
    equipment: list[str]
    cuisines: list[str]
    certifications: list[str]
    availability: list[str]
    external_sources: list[dict]


class CameraUploadRequest(BaseModel):
    """Photo upload payload for the kitchen camera feature."""

    kitchen_id: UUID
    file_name: str
    content_type: str
    file_size_bytes: int = Field(gt=0)
    image_base64: str | None = None


class CameraUploadResponse(BaseModel):
    """Result of a camera upload, returning compression statistics."""

    uploaded: bool
    compressed_size_bytes: int
    processing_latency_ms: int
    cache_key: str


class BiometricRegistrationRequest(BaseModel):
    """Register biometric credentials for quicker login."""

    device: DeviceInfo
    biometric_key: str = Field(min_length=10, max_length=255)


class BiometricRegistrationResponse(BaseModel):
    """Acknowledgement of biometric registration."""

    registered: bool
    registered_at: datetime


class BiometricVerificationRequest(BaseModel):
    """Verification payload for biometric login."""

    device_id: str
    signature: str


class BiometricVerificationResponse(BaseModel):
    """Result of biometric credential verification."""

    verified: bool
    tokens: MobileAuthTokens | None = None


class BiometricStatusResponse(BaseModel):
    """Current biometric enrollment status for a device."""

    device_id: str
    registered: bool
    registered_at: datetime | None


class PerformanceMetricsResponse(BaseModel):
    """Telemetry snapshot optimizing mobile performance."""

    latency_avg_ms: float
    latency_p95_ms: float
    offline_sync_success_rate: float
    last_sync_at: datetime | None
    issue_count: int


class PerformanceReportRequest(BaseModel):
    """User reported performance issue payload."""

    issue_type: Literal["latency", "crash", "battery", "other"]
    description: str = Field(min_length=5, max_length=500)
    occurred_at: datetime


class PerformanceReportResponse(BaseModel):
    """Acknowledgement of the reported performance issue."""

    accepted: bool
    reference_id: str


class BandwidthEstimateResponse(BaseModel):
    """Bandwidth optimization estimate for the client."""

    estimated_kbps: float
    basis: str
    last_measurement_at: datetime

