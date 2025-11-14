"""Domain service coordinating Kitchen Cam IoT operations."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.cache import RedisProtocol
from prep.models.orm import Booking, BookingStatus, Kitchen

from .schemas import (
    AccessGrantRequest,
    AccessGrantResponse,
    CameraInfo,
    CameraListResponse,
    CameraRecordRequest,
    CameraRecordResponse,
    CameraSnapshotResponse,
    CameraStreamResponse,
    DataExpireResponse,
    DeviceListResponse,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceRemovalResponse,
    DeviceUpdateRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    KitchenCamDevice,
    KitchenCamScheduleResponse,
    KitchenCamStatusResponse,
    LiveStatusResponse,
    LockCommandRequest,
    LockCommandResponse,
    LockStatusResponse,
    OccupancyResponse,
    PrivacyMode,
    PrivacyModeRequest,
    PrivacyModeResponse,
    PrivacyPoliciesResponse,
    PrivacyPolicy,
    PrivacyStatusResponse,
    ScheduleEntry,
    UsageEventRequest,
    UsageHistoryEvent,
    UsageHistoryResponse,
    UsageStatisticsResponse,
)


class KitchenCamService:
    """Central orchestrator for Kitchen Cam IoT features."""

    STATUS_CACHE_TTL = 30
    HEARTBEAT_TTL = 60 * 5
    HEARTBEAT_INTERVAL = 60
    PRIVACY_TTL = 60 * 60
    LOCK_TTL = 60 * 15
    ACCESS_TTL = 60 * 60
    DEVICE_REGISTRY_TTL = 60 * 60 * 24
    USAGE_EVENT_TTL = 60 * 60 * 24 * 14
    MAX_USAGE_EVENTS = 100

    def __init__(self, session: AsyncSession, redis: RedisProtocol) -> None:
        self.session = session
        self.redis = redis

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def kitchen_status(self, kitchen_id: UUID) -> KitchenCamStatusResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        cached = await self.redis.get(self._status_cache_key(kitchen_id))
        if isinstance(cached, str):
            try:
                return KitchenCamStatusResponse.model_validate_json(cached)
            except ValueError:
                pass

        now = datetime.now(UTC)
        lock_state = await self._get_lock_state(kitchen_id)
        privacy_state = await self._get_privacy_state(kitchen_id)
        heartbeat = await self._get_last_heartbeat(kitchen_id)
        occupancy = await self._resolve_occupancy(kitchen_id)
        alerts: list[str] = []
        if heartbeat and heartbeat.get("errors"):
            alerts.extend([str(err) for err in heartbeat["errors"]])

        status_str = "online" if heartbeat else "offline"
        if privacy_state.mode != PrivacyMode.OFF:
            status_str = "privacy"

        response = KitchenCamStatusResponse(
            kitchen_id=kitchen.id,
            kitchen_name=kitchen.name,
            status=status_str,
            lock_state="locked" if lock_state else "unlocked",
            privacy_mode=privacy_state.mode,
            occupancy=occupancy.occupant_count,
            last_heartbeat_at=heartbeat["recorded_at"] if heartbeat else None,
            updated_at=now,
            alerts=alerts,
            live_view_url=(
                f"https://stream.prep.local/kitchens/{kitchen_id}/primary"
                if status_str != "offline"
                else None
            ),
        )
        await self.redis.setex(
            self._status_cache_key(kitchen_id),
            self.STATUS_CACHE_TTL,
            response.model_dump_json(),
        )
        return response

    async def live_status(self, kitchen_id: UUID) -> LiveStatusResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        heartbeat = await self._get_last_heartbeat(kitchen_id)
        privacy_state = await self._get_privacy_state(kitchen_id)
        status_str = "online" if heartbeat else "offline"
        if privacy_state.mode != PrivacyMode.OFF:
            status_str = "privacy"

        bitrate = 2300 if status_str == "online" else 0
        last_frame = heartbeat["recorded_at"] if heartbeat else None
        return LiveStatusResponse(
            kitchen_id=kitchen.id,
            stream_url=f"https://stream.prep.local/kitchens/{kitchen_id}/primary.m3u8",
            status=status_str,
            bitrate_kbps=bitrate,
            last_frame_at=last_frame,
        )

    async def record_heartbeat(
        self, kitchen_id: UUID, payload: HeartbeatRequest
    ) -> HeartbeatResponse:
        await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        heartbeat_payload = {
            "kitchen_id": str(kitchen_id),
            "device_id": payload.device_id,
            "status": payload.status,
            "uptime_seconds": payload.uptime_seconds,
            "temperature_c": payload.temperature_c,
            "firmware_version": payload.firmware_version,
            "errors": payload.errors,
            "recorded_at": now.isoformat(),
        }
        await self.redis.setex(
            self._heartbeat_key(kitchen_id, payload.device_id),
            self.HEARTBEAT_TTL,
            json.dumps(heartbeat_payload),
        )
        await self.redis.setex(
            self._last_heartbeat_key(kitchen_id),
            self.HEARTBEAT_TTL,
            json.dumps(heartbeat_payload),
        )

        devices = await self._load_device_registry(kitchen_id)
        if payload.device_id in devices:
            device = devices[payload.device_id]
            device.last_heartbeat_at = now
            device.status = payload.status
            if payload.firmware_version:
                device.firmware_version = payload.firmware_version
            await self._persist_devices(kitchen_id, devices)

        lock_state = await self._get_lock_state(kitchen_id)
        return HeartbeatResponse(
            accepted=True,
            next_heartbeat_seconds=self.HEARTBEAT_INTERVAL,
            lock_state="locked" if lock_state else "unlocked",
        )

    async def schedule(self, kitchen_id: UUID) -> KitchenCamScheduleResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        window_start = now - timedelta(days=1)
        window_end = now + timedelta(days=7)

        stmt = (
            select(Booking)
            .where(Booking.kitchen_id == kitchen_id)
            .where(Booking.start_time >= window_start)
            .where(Booking.start_time <= window_end)
            .where(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]))
            .order_by(Booking.start_time.asc())
        )
        result = await self.session.execute(stmt)
        bookings = result.scalars().unique().all()

        items = [
            ScheduleEntry(
                booking_id=booking.id,
                start_time=booking.start_time,
                end_time=booking.end_time,
                customer_name=None,
                status=booking.status.value,
            )
            for booking in bookings
        ]
        return KitchenCamScheduleResponse(
            kitchen_id=kitchen.id,
            items=items,
            generated_at=now,
        )

    async def lock(self, kitchen_id: UUID, payload: LockCommandRequest) -> LockCommandResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        data = {
            "locked": True,
            "updated_at": now.isoformat(),
            "requested_by": payload.requested_by,
            "reason": payload.reason,
            "source": "api",
        }
        await self.redis.setex(
            self._lock_key(kitchen_id),
            self.LOCK_TTL,
            json.dumps(data),
        )
        await self._enqueue_security_alert(kitchen_id, "lock", payload.requested_by)
        return LockCommandResponse(
            kitchen_id=kitchen.id,
            locked=True,
            effective_at=now,
            expires_at=now + timedelta(seconds=self.LOCK_TTL),
            issued_by=payload.requested_by,
            reason=payload.reason,
        )

    async def unlock(self, kitchen_id: UUID, payload: LockCommandRequest) -> LockCommandResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        data = {
            "locked": False,
            "updated_at": now.isoformat(),
            "requested_by": payload.requested_by,
            "reason": payload.reason,
            "source": "api",
        }
        await self.redis.setex(
            self._lock_key(kitchen_id),
            self.LOCK_TTL,
            json.dumps(data),
        )
        await self._enqueue_security_alert(kitchen_id, "unlock", payload.requested_by)
        return LockCommandResponse(
            kitchen_id=kitchen.id,
            locked=False,
            effective_at=now,
            expires_at=now + timedelta(seconds=self.LOCK_TTL),
            issued_by=payload.requested_by,
            reason=payload.reason,
        )

    async def lock_status(self, kitchen_id: UUID) -> LockStatusResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        payload = await self.redis.get(self._lock_key(kitchen_id))
        now = datetime.now(UTC)
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except ValueError:
                data = {}
        else:
            data = {}
        locked = bool(data.get("locked", False))
        updated_at = self._parse_datetime(data.get("updated_at")) or now
        last_command = "lock" if locked else "unlock"
        return LockStatusResponse(
            kitchen_id=kitchen.id,
            locked=locked,
            updated_at=updated_at,
            last_command=last_command,
            source=data.get("source"),
        )

    async def grant_access(
        self, kitchen_id: UUID, payload: AccessGrantRequest
    ) -> AccessGrantResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        code = token_urlsafe(6)
        data = {
            "access_code": code,
            "expires_at": payload.expires_at.isoformat(),
            "recipient": {
                "email": payload.recipient_email,
                "name": payload.recipient_name,
            },
        }
        await self.redis.setex(
            self._access_key(kitchen_id, code),
            self.ACCESS_TTL,
            json.dumps(data),
        )
        await self._enqueue_security_alert(
            kitchen_id,
            "access_granted",
            payload.recipient_email,
        )
        return AccessGrantResponse(
            kitchen_id=kitchen.id,
            granted=True,
            access_code=code,
            expires_at=payload.expires_at,
            notified=True,
        )

    async def usage_statistics(self, kitchen_id: UUID) -> UsageStatisticsResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        window_start = now - timedelta(days=30)
        stmt = (
            select(Booking)
            .where(Booking.kitchen_id == kitchen_id)
            .where(Booking.start_time >= window_start)
        )
        result = await self.session.execute(stmt)
        bookings = result.scalars().unique().all()
        active_hours = 0.0
        for booking in bookings:
            delta = booking.end_time - booking.start_time
            active_hours += round(delta.total_seconds() / 3600, 2)
        event_count = len(await self._load_usage_events(kitchen_id))
        utilization_rate = 0.0
        if bookings:
            utilization_rate = min(1.0, active_hours / (30 * 24))
        return UsageStatisticsResponse(
            kitchen_id=kitchen.id,
            timeframe_start=window_start,
            timeframe_end=now,
            active_hours=round(active_hours, 2),
            booking_count=len(bookings),
            event_count=event_count,
            utilization_rate=round(utilization_rate, 3),
            generated_at=now,
        )

    async def usage_history(self, kitchen_id: UUID) -> UsageHistoryResponse:
        await self._get_kitchen(kitchen_id)
        events = await self._load_usage_events(kitchen_id)
        return UsageHistoryResponse(
            kitchen_id=kitchen_id,
            events=events,
            generated_at=datetime.now(UTC),
        )

    async def log_usage_event(
        self, kitchen_id: UUID, payload: UsageEventRequest
    ) -> UsageHistoryResponse:
        await self._get_kitchen(kitchen_id)
        events = await self._load_usage_events(kitchen_id)
        recorded_at = payload.recorded_at or datetime.now(UTC)
        event = UsageHistoryEvent(
            event_type=payload.event_type,
            recorded_at=recorded_at,
            metadata=payload.metadata,
        )
        events.append(event)
        events = events[-self.MAX_USAGE_EVENTS :]
        await self._persist_usage_events(kitchen_id, events)
        await self._enqueue_security_alert(kitchen_id, "usage_event", payload.event_type)
        return UsageHistoryResponse(
            kitchen_id=kitchen_id,
            events=events,
            generated_at=datetime.now(UTC),
        )

    async def occupancy(self, kitchen_id: UUID) -> OccupancyResponse:
        await self._get_kitchen(kitchen_id)
        return await self._resolve_occupancy(kitchen_id)

    async def camera_list(self, kitchen_id: UUID) -> CameraListResponse:
        kitchen = await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        items: list[CameraInfo] = [
            CameraInfo(
                camera_id="primary",
                name="Primary Line",
                location=(kitchen.city or "main").lower(),
                status="online",
            ),
            CameraInfo(
                camera_id="prep-line",
                name="Prep Line",
                location="prep",
                status="online",
            ),
        ]
        return CameraListResponse(
            kitchen_id=kitchen.id,
            items=items,
            generated_at=now,
        )

    async def camera_snapshot(self, kitchen_id: UUID, camera_id: str) -> CameraSnapshotResponse:
        await self._ensure_camera(camera_id)
        await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        return CameraSnapshotResponse(
            kitchen_id=kitchen_id,
            camera_id=camera_id,
            snapshot_url=f"https://media.prep.local/kitchens/{kitchen_id}/{camera_id}/snapshot.jpg",
            captured_at=now,
        )

    async def camera_stream(self, kitchen_id: UUID, camera_id: str) -> CameraStreamResponse:
        await self._ensure_camera(camera_id)
        await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        return CameraStreamResponse(
            kitchen_id=kitchen_id,
            camera_id=camera_id,
            stream_url=f"https://stream.prep.local/kitchens/{kitchen_id}/{camera_id}.m3u8",
            expires_at=now + timedelta(minutes=10),
        )

    async def camera_record(
        self, kitchen_id: UUID, camera_id: str, payload: CameraRecordRequest
    ) -> CameraRecordResponse:
        await self._ensure_camera(camera_id)
        await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        recording_id = token_urlsafe(8)
        await self._enqueue_security_alert(
            kitchen_id,
            "recording",
            f"{camera_id}:{payload.duration_seconds}",
        )
        return CameraRecordResponse(
            kitchen_id=kitchen_id,
            camera_id=camera_id,
            recording_id=recording_id,
            expires_at=now + timedelta(hours=24),
        )

    async def set_privacy_mode(
        self, kitchen_id: UUID, payload: PrivacyModeRequest
    ) -> PrivacyModeResponse:
        await self._get_kitchen(kitchen_id)
        now = datetime.now(UTC)
        expires_at = (
            now + timedelta(minutes=payload.duration_minutes) if payload.duration_minutes else None
        )
        privacy_payload = {
            "mode": payload.mode.value,
            "effective_at": now.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "reason": payload.reason,
            "requested_by": payload.requested_by,
        }
        await self.redis.setex(
            self._privacy_key(kitchen_id),
            self.PRIVACY_TTL,
            json.dumps(privacy_payload),
        )
        return PrivacyModeResponse(
            kitchen_id=kitchen_id,
            mode=payload.mode,
            effective_at=now,
            expires_at=expires_at,
            reason=payload.reason,
            requested_by=payload.requested_by,
        )

    async def privacy_status(self, kitchen_id: UUID) -> PrivacyStatusResponse:
        await self._get_kitchen(kitchen_id)
        state = await self._get_privacy_state(kitchen_id)
        is_enforced = state.mode != PrivacyMode.OFF and (
            state.expires_at is None or state.expires_at > datetime.now(UTC)
        )
        return PrivacyStatusResponse(
            kitchen_id=kitchen_id,
            mode=state.mode,
            effective_at=state.effective_at,
            expires_at=state.expires_at,
            is_privacy_enforced=is_enforced,
        )

    async def expire_data(self, kitchen_id: UUID, before: datetime) -> DataExpireResponse:
        await self._get_kitchen(kitchen_id)
        task_payload = {
            "purge_before": before.isoformat(),
            "scheduled_at": datetime.now(UTC).isoformat(),
        }
        await self.redis.setex(
            self._data_expire_key(kitchen_id),
            self.PRIVACY_TTL,
            json.dumps(task_payload),
        )
        await self._enqueue_security_alert(kitchen_id, "data_expire", before.isoformat())
        return DataExpireResponse(kitchen_id=kitchen_id, scheduled=True, purge_after=before)

    async def privacy_policies(self) -> PrivacyPoliciesResponse:
        now = datetime.now(UTC)
        items = [
            PrivacyPolicy(
                id="gdpr",
                title="GDPR Compliance",
                description="Data minimization, retention controls, and subject access workflows.",
                region="EU",
                updated_at=now,
            ),
            PrivacyPolicy(
                id="ccpa",
                title="CCPA Compliance",
                description="Deletion workflows and opt-out preferences for California residents.",
                region="US-CA",
                updated_at=now,
            ),
        ]
        return PrivacyPoliciesResponse(items=items, generated_at=now)

    async def register_device(
        self, kitchen_id: UUID, payload: DeviceRegistrationRequest
    ) -> DeviceRegistrationResponse:
        await self._get_kitchen(kitchen_id)
        devices = await self._load_device_registry(kitchen_id)
        now = datetime.now(UTC)
        created = payload.device_id not in devices
        device = devices.get(
            payload.device_id,
            KitchenCamDevice(
                device_id=payload.device_id,
                device_type=payload.device_type,
                firmware_version=payload.firmware_version,
                capabilities=payload.capabilities,
                registered_at=now,
            ),
        )
        if not created:
            if payload.device_type:
                device.device_type = payload.device_type
            if payload.firmware_version:
                device.firmware_version = payload.firmware_version
            if payload.capabilities:
                device.capabilities = payload.capabilities
        else:
            device.registered_at = now
        devices[payload.device_id] = device
        await self._persist_devices(kitchen_id, devices)
        return DeviceRegistrationResponse(
            kitchen_id=kitchen_id,
            device=device,
            created=created,
        )

    async def update_device(
        self, kitchen_id: UUID, device_id: str, payload: DeviceUpdateRequest
    ) -> DeviceRegistrationResponse:
        await self._get_kitchen(kitchen_id)
        devices = await self._load_device_registry(kitchen_id)
        if device_id not in devices:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        device = devices[device_id]
        if payload.device_type:
            device.device_type = payload.device_type
        if payload.firmware_version:
            device.firmware_version = payload.firmware_version
        if payload.capabilities is not None:
            device.capabilities = payload.capabilities
        if payload.status:
            device.status = payload.status
        await self._persist_devices(kitchen_id, devices)
        return DeviceRegistrationResponse(
            kitchen_id=kitchen_id,
            device=device,
            created=False,
        )

    async def remove_device(self, kitchen_id: UUID, device_id: str) -> DeviceRemovalResponse:
        await self._get_kitchen(kitchen_id)
        devices = await self._load_device_registry(kitchen_id)
        removed = devices.pop(device_id, None)
        if removed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        await self._persist_devices(kitchen_id, devices)
        return DeviceRemovalResponse(
            kitchen_id=kitchen_id,
            device_id=device_id,
            removed=True,
            remaining=len(devices),
        )

    async def list_devices(self, kitchen_id: UUID) -> DeviceListResponse:
        await self._get_kitchen(kitchen_id)
        devices = await self._load_device_registry(kitchen_id)
        now = datetime.now(UTC)
        return DeviceListResponse(
            kitchen_id=kitchen_id,
            devices=list(devices.values()),
            generated_at=now,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_kitchen(self, kitchen_id: UUID) -> Kitchen:
        kitchen = await self.session.get(Kitchen, kitchen_id)
        if kitchen is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
        return kitchen

    async def _get_last_heartbeat(self, kitchen_id: UUID) -> dict[str, Any] | None:
        payload = await self.redis.get(self._last_heartbeat_key(kitchen_id))
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except ValueError:
                return None
            data["recorded_at"] = self._parse_datetime(data.get("recorded_at"))
            return data
        return None

    async def _get_lock_state(self, kitchen_id: UUID) -> bool:
        payload = await self.redis.get(self._lock_key(kitchen_id))
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except ValueError:
                return False
            return bool(data.get("locked", False))
        return False

    async def _get_privacy_state(self, kitchen_id: UUID) -> PrivacyModeResponse:
        payload = await self.redis.get(self._privacy_key(kitchen_id))
        now = datetime.now(UTC)
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except ValueError:
                data = {}
            raw_mode = data.get("mode", PrivacyMode.OFF.value)
            mode = PrivacyMode(raw_mode)
            effective_at = self._parse_datetime(data.get("effective_at")) or now
            expires_at = self._parse_datetime(data.get("expires_at"))
            return PrivacyModeResponse(
                kitchen_id=kitchen_id,
                mode=mode,
                effective_at=effective_at,
                expires_at=expires_at,
                reason=data.get("reason"),
                requested_by=data.get("requested_by"),
            )
        return PrivacyModeResponse(
            kitchen_id=kitchen_id,
            mode=PrivacyMode.OFF,
            effective_at=now,
            expires_at=None,
            reason=None,
            requested_by=None,
        )

    async def _resolve_occupancy(self, kitchen_id: UUID) -> OccupancyResponse:
        now = datetime.now(UTC)
        stmt = (
            select(Booking)
            .where(Booking.kitchen_id == kitchen_id)
            .where(Booking.status == BookingStatus.CONFIRMED)
            .where(Booking.start_time <= now)
            .where(Booking.end_time >= now)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        booking = result.scalars().first()
        occupied = booking is not None
        occupant_count = 1 if occupied else 0
        return OccupancyResponse(
            kitchen_id=kitchen_id,
            is_occupied=occupied,
            occupant_count=occupant_count,
            active_booking_id=booking.id if booking else None,
            source="booking",
            checked_at=now,
        )

    async def _load_usage_events(self, kitchen_id: UUID) -> list[UsageHistoryEvent]:
        payload = await self.redis.get(self._usage_key(kitchen_id))
        if isinstance(payload, str):
            try:
                raw_events = json.loads(payload)
            except ValueError:
                return []
            events: list[UsageHistoryEvent] = []
            for item in raw_events:
                events.append(
                    UsageHistoryEvent(
                        event_type=item.get("event_type", "unknown"),
                        recorded_at=self._parse_datetime(item.get("recorded_at"))
                        or datetime.now(UTC),
                        metadata=item.get("metadata", {}),
                    )
                )
            return events
        return []

    async def _persist_usage_events(
        self, kitchen_id: UUID, events: list[UsageHistoryEvent]
    ) -> None:
        payload = [
            {
                "event_type": event.event_type,
                "recorded_at": event.recorded_at.isoformat(),
                "metadata": event.metadata,
            }
            for event in events
        ]
        await self.redis.setex(
            self._usage_key(kitchen_id),
            self.USAGE_EVENT_TTL,
            json.dumps(payload),
        )

    async def _load_device_registry(self, kitchen_id: UUID) -> dict[str, KitchenCamDevice]:
        payload = await self.redis.get(self._devices_key(kitchen_id))
        devices: dict[str, KitchenCamDevice] = {}
        if isinstance(payload, str):
            try:
                raw_devices = json.loads(payload)
            except ValueError:
                raw_devices = {}
            for device_id, data in raw_devices.items():
                devices[device_id] = KitchenCamDevice(
                    device_id=device_id,
                    device_type=data.get("device_type", "unknown"),
                    firmware_version=data.get("firmware_version"),
                    capabilities=data.get("capabilities", []),
                    registered_at=self._parse_datetime(data.get("registered_at"))
                    or datetime.now(UTC),
                    last_heartbeat_at=self._parse_datetime(data.get("last_heartbeat_at")),
                    status=data.get("status"),
                )
        return devices

    async def _persist_devices(
        self, kitchen_id: UUID, devices: dict[str, KitchenCamDevice]
    ) -> None:
        payload = {
            device_id: {
                "device_type": device.device_type,
                "firmware_version": device.firmware_version,
                "capabilities": device.capabilities,
                "registered_at": device.registered_at.isoformat(),
                "last_heartbeat_at": device.last_heartbeat_at.isoformat()
                if device.last_heartbeat_at
                else None,
                "status": device.status,
            }
            for device_id, device in devices.items()
        }
        await self.redis.setex(
            self._devices_key(kitchen_id),
            self.DEVICE_REGISTRY_TTL,
            json.dumps(payload),
        )

    async def _enqueue_security_alert(
        self, kitchen_id: UUID, event_type: str, actor: str | None
    ) -> None:
        alert = {
            "event": event_type,
            "actor": actor,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        await self.redis.setex(
            self._alerts_key(kitchen_id),
            self.STATUS_CACHE_TTL,
            json.dumps(alert),
        )

    async def _ensure_camera(self, camera_id: str) -> None:
        if camera_id not in {"primary", "prep-line"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _status_cache_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:status:{kitchen_id}"

    @staticmethod
    def _last_heartbeat_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:last_heartbeat:{kitchen_id}"

    @staticmethod
    def _heartbeat_key(kitchen_id: UUID, device_id: str) -> str:
        return f"kitchen_cam:heartbeat:{kitchen_id}:{device_id}"

    @staticmethod
    def _lock_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:lock:{kitchen_id}"

    @staticmethod
    def _access_key(kitchen_id: UUID, code: str) -> str:
        return f"kitchen_cam:access:{kitchen_id}:{code}"

    @staticmethod
    def _usage_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:usage:{kitchen_id}"

    @staticmethod
    def _privacy_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:privacy:{kitchen_id}"

    @staticmethod
    def _data_expire_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:data_expire:{kitchen_id}"

    @staticmethod
    def _devices_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:devices:{kitchen_id}"

    @staticmethod
    def _alerts_key(kitchen_id: UUID) -> str:
        return f"kitchen_cam:alerts:{kitchen_id}"
