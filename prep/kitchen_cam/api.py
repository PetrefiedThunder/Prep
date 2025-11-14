"""FastAPI router exposing the Kitchen Cam IoT API surface."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import get_current_user
from prep.cache import RedisProtocol, get_redis
from prep.database import get_db
from prep.models.orm import User

from .schemas import (
    AccessGrantRequest,
    AccessGrantResponse,
    CameraListResponse,
    CameraRecordRequest,
    CameraRecordResponse,
    CameraSnapshotResponse,
    CameraStreamResponse,
    DataExpireRequest,
    DataExpireResponse,
    DeviceListResponse,
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceRemovalResponse,
    DeviceUpdateRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    KitchenCamScheduleResponse,
    KitchenCamStatusResponse,
    LiveStatusResponse,
    LockCommandRequest,
    LockCommandResponse,
    LockStatusResponse,
    OccupancyResponse,
    PrivacyModeRequest,
    PrivacyModeResponse,
    PrivacyPoliciesResponse,
    PrivacyStatusResponse,
    UsageEventRequest,
    UsageHistoryResponse,
    UsageStatisticsResponse,
)
from .service import KitchenCamService

router = APIRouter(prefix="/api/v2/kitchen-cam", tags=["kitchen-cam"])


async def get_kitchen_cam_service(
    session: AsyncSession = Depends(get_db),
    redis: RedisProtocol = Depends(get_redis),
) -> KitchenCamService:
    return KitchenCamService(session, redis)


@router.get("/{kitchen_id}/status", response_model=KitchenCamStatusResponse)
async def kitchen_status(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> KitchenCamStatusResponse:
    _ = current_user
    return await service.kitchen_status(kitchen_id)


@router.get("/{kitchen_id}/live", response_model=LiveStatusResponse)
async def live_status(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> LiveStatusResponse:
    _ = current_user
    return await service.live_status(kitchen_id)


@router.post("/{kitchen_id}/heartbeat", response_model=HeartbeatResponse)
async def device_heartbeat(
    kitchen_id: UUID,
    payload: HeartbeatRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> HeartbeatResponse:
    _ = current_user
    return await service.record_heartbeat(kitchen_id, payload)


@router.get("/{kitchen_id}/schedule", response_model=KitchenCamScheduleResponse)
async def kitchen_schedule(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> KitchenCamScheduleResponse:
    _ = current_user
    return await service.schedule(kitchen_id)


@router.post("/{kitchen_id}/lock", response_model=LockCommandResponse)
async def lock_kitchen(
    kitchen_id: UUID,
    payload: LockCommandRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> LockCommandResponse:
    _ = current_user
    return await service.lock(kitchen_id, payload)


@router.post("/{kitchen_id}/unlock", response_model=LockCommandResponse)
async def unlock_kitchen(
    kitchen_id: UUID,
    payload: LockCommandRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> LockCommandResponse:
    _ = current_user
    return await service.unlock(kitchen_id, payload)


@router.get("/{kitchen_id}/lock/status", response_model=LockStatusResponse)
async def lock_status(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> LockStatusResponse:
    _ = current_user
    return await service.lock_status(kitchen_id)


@router.post("/{kitchen_id}/access/grant", response_model=AccessGrantResponse)
async def grant_access(
    kitchen_id: UUID,
    payload: AccessGrantRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> AccessGrantResponse:
    _ = current_user
    return await service.grant_access(kitchen_id, payload)


@router.get("/{kitchen_id}/usage", response_model=UsageStatisticsResponse)
async def usage_statistics(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> UsageStatisticsResponse:
    _ = current_user
    return await service.usage_statistics(kitchen_id)


@router.get("/{kitchen_id}/usage/history", response_model=UsageHistoryResponse)
async def usage_history(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> UsageHistoryResponse:
    _ = current_user
    return await service.usage_history(kitchen_id)


@router.post("/{kitchen_id}/usage/event", response_model=UsageHistoryResponse)
async def log_usage_event(
    kitchen_id: UUID,
    payload: UsageEventRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> UsageHistoryResponse:
    _ = current_user
    return await service.log_usage_event(kitchen_id, payload)


@router.get("/{kitchen_id}/occupancy", response_model=OccupancyResponse)
async def occupancy_status(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> OccupancyResponse:
    _ = current_user
    return await service.occupancy(kitchen_id)


@router.get("/{kitchen_id}/cameras", response_model=CameraListResponse)
async def camera_list(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> CameraListResponse:
    _ = current_user
    return await service.camera_list(kitchen_id)


@router.get("/{kitchen_id}/cameras/{camera_id}/snapshot", response_model=CameraSnapshotResponse)
async def camera_snapshot(
    kitchen_id: UUID,
    camera_id: str,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> CameraSnapshotResponse:
    _ = current_user
    return await service.camera_snapshot(kitchen_id, camera_id)


@router.get("/{kitchen_id}/cameras/{camera_id}/stream", response_model=CameraStreamResponse)
async def camera_stream(
    kitchen_id: UUID,
    camera_id: str,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> CameraStreamResponse:
    _ = current_user
    return await service.camera_stream(kitchen_id, camera_id)


@router.post("/{kitchen_id}/cameras/{camera_id}/record", response_model=CameraRecordResponse)
async def camera_record(
    kitchen_id: UUID,
    camera_id: str,
    payload: CameraRecordRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> CameraRecordResponse:
    _ = current_user
    return await service.camera_record(kitchen_id, camera_id, payload)


@router.post("/{kitchen_id}/privacy/mode", response_model=PrivacyModeResponse)
async def set_privacy_mode(
    kitchen_id: UUID,
    payload: PrivacyModeRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> PrivacyModeResponse:
    _ = current_user
    return await service.set_privacy_mode(kitchen_id, payload)


@router.get("/{kitchen_id}/privacy/status", response_model=PrivacyStatusResponse)
async def privacy_status(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> PrivacyStatusResponse:
    _ = current_user
    return await service.privacy_status(kitchen_id)


@router.post("/{kitchen_id}/data/expire", response_model=DataExpireResponse)
async def expire_data(
    kitchen_id: UUID,
    payload: DataExpireRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> DataExpireResponse:
    _ = current_user
    return await service.expire_data(kitchen_id, payload.before)


@router.get("/privacy/policies", response_model=PrivacyPoliciesResponse)
async def privacy_policies(
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> PrivacyPoliciesResponse:
    _ = current_user
    return await service.privacy_policies()


@router.get("/{kitchen_id}/devices", response_model=DeviceListResponse)
async def list_devices(
    kitchen_id: UUID,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> DeviceListResponse:
    _ = current_user
    return await service.list_devices(kitchen_id)


@router.post("/{kitchen_id}/devices/register", response_model=DeviceRegistrationResponse)
async def register_device(
    kitchen_id: UUID,
    payload: DeviceRegistrationRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> DeviceRegistrationResponse:
    _ = current_user
    return await service.register_device(kitchen_id, payload)


@router.post("/{kitchen_id}/devices/{device_id}/update", response_model=DeviceRegistrationResponse)
async def update_device(
    kitchen_id: UUID,
    device_id: str,
    payload: DeviceUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> DeviceRegistrationResponse:
    _ = current_user
    return await service.update_device(kitchen_id, device_id, payload)


@router.delete("/{kitchen_id}/devices/{device_id}", response_model=DeviceRemovalResponse)
async def remove_device(
    kitchen_id: UUID,
    device_id: str,
    current_user: User = Depends(get_current_user),
    service: KitchenCamService = Depends(get_kitchen_cam_service),
) -> DeviceRemovalResponse:
    _ = current_user
    return await service.remove_device(kitchen_id, device_id)
