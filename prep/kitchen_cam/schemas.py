"""Pydantic schemas powering the Kitchen Cam IoT API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PrivacyMode(str, Enum):
    """Enumerates privacy states supported by the camera system."""

    OFF = "off"
    ON = "on"
    SCHEDULED = "scheduled"


class KitchenCamDevice(BaseModel):
    """Registered Kitchen Cam hardware device."""

    device_id: str = Field(min_length=3, max_length=255)
    device_type: str = Field(min_length=3, max_length=120)
    firmware_version: str | None = Field(default=None, max_length=120)
    capabilities: list[str] = Field(default_factory=list)
    registered_at: datetime
    last_heartbeat_at: datetime | None = None
    status: str | None = None


class KitchenCamStatusResponse(BaseModel):
    """High level operational status for the Kitchen Cam system."""

    kitchen_id: UUID
    kitchen_name: str
    status: str
    lock_state: str
    privacy_mode: PrivacyMode
    occupancy: int
    last_heartbeat_at: datetime | None = None
    updated_at: datetime
    alerts: list[str] = Field(default_factory=list)
    live_view_url: str | None = None


class LiveStatusResponse(BaseModel):
    """Represents a live stream status payload."""

    kitchen_id: UUID
    stream_url: str
    status: str
    bitrate_kbps: int
    last_frame_at: datetime | None = None


class HeartbeatRequest(BaseModel):
    """Device heartbeat payload sent by the IoT camera."""

    device_id: str = Field(min_length=3, max_length=255)
    status: str = Field(min_length=3, max_length=120)
    uptime_seconds: int = Field(ge=0)
    temperature_c: float | None = None
    firmware_version: str | None = Field(default=None, max_length=120)
    errors: list[str] = Field(default_factory=list)


class HeartbeatResponse(BaseModel):
    """Acknowledgement returned after a heartbeat is processed."""

    accepted: bool
    next_heartbeat_seconds: int
    lock_state: str


class ScheduleEntry(BaseModel):
    """Represents a scheduled booking for the kitchen."""

    booking_id: UUID
    start_time: datetime
    end_time: datetime
    customer_name: str | None = None
    status: str


class KitchenCamScheduleResponse(BaseModel):
    """Schedule payload for the camera usage window."""

    kitchen_id: UUID
    items: list[ScheduleEntry]
    generated_at: datetime


class LockCommandRequest(BaseModel):
    """Lock or unlock command metadata."""

    requested_by: str | None = Field(default=None, max_length=120)
    reason: str | None = Field(default=None, max_length=255)


class LockCommandResponse(BaseModel):
    """Response envelope for lock and unlock commands."""

    kitchen_id: UUID
    locked: bool
    effective_at: datetime
    expires_at: datetime | None = None
    issued_by: str | None = None
    reason: str | None = None


class LockStatusResponse(BaseModel):
    """Current smart lock state."""

    kitchen_id: UUID
    locked: bool
    updated_at: datetime
    last_command: str | None = None
    source: str | None = None


class AccessGrantRequest(BaseModel):
    """Request payload granting short-lived kitchen access."""

    recipient_email: str = Field(min_length=3, max_length=255)
    recipient_name: str | None = Field(default=None, max_length=255)
    access_level: str = Field(default="temporary", max_length=120)
    expires_at: datetime


class AccessGrantResponse(BaseModel):
    """Confirmation payload for temporary access grants."""

    kitchen_id: UUID
    granted: bool
    access_code: str
    expires_at: datetime
    notified: bool


class UsageStatisticsResponse(BaseModel):
    """Aggregated utilization metrics for a kitchen."""

    kitchen_id: UUID
    timeframe_start: datetime
    timeframe_end: datetime
    active_hours: float
    booking_count: int
    event_count: int
    utilization_rate: float
    generated_at: datetime


class UsageHistoryEvent(BaseModel):
    """Recorded usage event for auditing."""

    event_type: str
    recorded_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageHistoryResponse(BaseModel):
    """Historical usage timeline for analytics."""

    kitchen_id: UUID
    events: list[UsageHistoryEvent]
    generated_at: datetime


class UsageEventRequest(BaseModel):
    """Payload logging a custom usage event."""

    event_type: str = Field(min_length=3, max_length=120)
    recorded_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OccupancyResponse(BaseModel):
    """Real-time occupancy snapshot."""

    kitchen_id: UUID
    is_occupied: bool
    occupant_count: int
    active_booking_id: UUID | None = None
    source: str
    checked_at: datetime


class CameraInfo(BaseModel):
    """Metadata describing a camera at the kitchen."""

    camera_id: str
    name: str
    location: str | None = None
    status: str


class CameraListResponse(BaseModel):
    """List of cameras available for a kitchen."""

    kitchen_id: UUID
    items: list[CameraInfo]
    generated_at: datetime


class CameraSnapshotResponse(BaseModel):
    """Snapshot metadata for a camera."""

    kitchen_id: UUID
    camera_id: str
    snapshot_url: str
    captured_at: datetime


class CameraStreamResponse(BaseModel):
    """Stream descriptor for a camera."""

    kitchen_id: UUID
    camera_id: str
    stream_url: str
    expires_at: datetime


class CameraRecordRequest(BaseModel):
    """Recording command payload."""

    duration_seconds: int = Field(ge=10, le=3600)
    quality: str | None = Field(default="hd", max_length=50)


class CameraRecordResponse(BaseModel):
    """Recording command acknowledgement."""

    kitchen_id: UUID
    camera_id: str
    recording_id: str
    expires_at: datetime


class PrivacyModeRequest(BaseModel):
    """Privacy mode change request."""

    mode: PrivacyMode
    reason: str | None = Field(default=None, max_length=255)
    requested_by: str | None = Field(default=None, max_length=120)
    duration_minutes: int | None = Field(default=None, ge=5, le=720)


class PrivacyModeResponse(BaseModel):
    """Response after applying a privacy mode change."""

    kitchen_id: UUID
    mode: PrivacyMode
    effective_at: datetime
    expires_at: datetime | None
    reason: str | None = None
    requested_by: str | None = None


class PrivacyStatusResponse(BaseModel):
    """Current privacy posture for the kitchen."""

    kitchen_id: UUID
    mode: PrivacyMode
    effective_at: datetime
    expires_at: datetime | None
    is_privacy_enforced: bool


class DataExpireRequest(BaseModel):
    """Request to purge recorded data prior to a timestamp."""

    before: datetime
    requested_by: str | None = Field(default=None, max_length=120)


class DataExpireResponse(BaseModel):
    """Response acknowledging data expiration tasks."""

    kitchen_id: UUID
    scheduled: bool
    purge_after: datetime


class PrivacyPolicy(BaseModel):
    """Policy record describing privacy compliance posture."""

    id: str
    title: str
    description: str
    region: str
    updated_at: datetime


class PrivacyPoliciesResponse(BaseModel):
    """List of privacy and compliance policies."""

    items: list[PrivacyPolicy]
    generated_at: datetime


class DeviceRegistrationRequest(BaseModel):
    """Register a new device for the kitchen."""

    device_id: str = Field(min_length=3, max_length=255)
    device_type: str = Field(min_length=3, max_length=120)
    firmware_version: str | None = Field(default=None, max_length=120)
    capabilities: list[str] = Field(default_factory=list)


class DeviceRegistrationResponse(BaseModel):
    """Response for device registration and update operations."""

    kitchen_id: UUID
    device: KitchenCamDevice
    created: bool


class DeviceUpdateRequest(BaseModel):
    """Update metadata for an existing device."""

    device_type: str | None = Field(default=None, max_length=120)
    firmware_version: str | None = Field(default=None, max_length=120)
    capabilities: list[str] | None = None
    status: str | None = Field(default=None, max_length=120)


class DeviceListResponse(BaseModel):
    """Registered device inventory for a kitchen."""

    kitchen_id: UUID
    devices: list[KitchenCamDevice]
    generated_at: datetime


class DeviceRemovalResponse(BaseModel):
    """Response when a device is removed from the registry."""

    kitchen_id: UUID
    device_id: str
    removed: bool
    remaining: int
