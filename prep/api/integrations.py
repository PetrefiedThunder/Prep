from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import get_current_user
from prep.database.connection import get_db
from prep.models.orm import Integration, IntegrationStatus, User, UserRole

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationBase(BaseModel):
    service_type: str
    vendor_name: str
    auth_method: str
    sync_frequency: str
    kitchen_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrationCreate(IntegrationBase):
    status: IntegrationStatus = Field(default=IntegrationStatus.ACTIVE)
    user_id: UUID | None = None


class IntegrationUpdate(BaseModel):
    service_type: str | None = None
    vendor_name: str | None = None
    auth_method: str | None = None
    sync_frequency: str | None = None
    status: IntegrationStatus | None = None
    kitchen_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class IntegrationResponse(BaseModel):
    id: UUID
    user_id: UUID
    kitchen_id: UUID | None = None
    service_type: str
    vendor_name: str
    auth_method: str
    sync_frequency: str
    status: IntegrationStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


def _is_admin(user: User) -> bool:
    return bool(user.is_admin or user.role is UserRole.ADMIN)


def _require_role(user: User, roles: Collection[UserRole]) -> None:
    if _is_admin(user):
        return
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _serialize_integration(record: Integration) -> IntegrationResponse:
    return IntegrationResponse(
        id=record.id,
        user_id=record.user_id,
        kitchen_id=record.kitchen_id,
        service_type=record.service_type,
        vendor_name=record.vendor_name,
        auth_method=record.auth_method,
        sync_frequency=record.sync_frequency,
        status=record.status,
        metadata=record.metadata_json or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _apply_visibility_filters(query: Select[tuple[Integration]], user: User) -> Select[tuple[Integration]]:
    if _is_admin(user):
        return query
    return query.where(Integration.user_id == user.id)


async def _get_integration_or_404(session: AsyncSession, integration_id: UUID) -> Integration:
    integration = await session.get(Integration, integration_id)
    if integration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    return integration


@router.get("/", response_model=list[IntegrationResponse])
async def list_integrations(
    kitchen_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IntegrationResponse]:
    _require_role(current_user, {UserRole.HOST, UserRole.CUSTOMER})

    query: Select[tuple[Integration]] = select(Integration).order_by(Integration.created_at.desc())
    if kitchen_id is not None:
        query = query.where(Integration.kitchen_id == kitchen_id)
    query = _apply_visibility_filters(query, current_user)

    result = await session.execute(query)
    records = result.scalars().all()
    return [_serialize_integration(record) for record in records]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationResponse:
    _require_role(current_user, {UserRole.HOST, UserRole.CUSTOMER})
    integration = await _get_integration_or_404(session, integration_id)

    if not _is_admin(current_user) and integration.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    return _serialize_integration(integration)


@router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    payload: IntegrationCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationResponse:
    _require_role(current_user, {UserRole.HOST})

    owner_id = payload.user_id or current_user.id
    if not _is_admin(current_user) and owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign integrations to other users")

    integration = Integration(
        user_id=owner_id,
        kitchen_id=payload.kitchen_id,
        service_type=payload.service_type,
        vendor_name=payload.vendor_name,
        auth_method=payload.auth_method,
        sync_frequency=payload.sync_frequency,
        status=payload.status,
        metadata_json=payload.metadata or {},
    )

    session.add(integration)
    await session.commit()
    await session.refresh(integration)

    return _serialize_integration(integration)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    payload: IntegrationUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationResponse:
    _require_role(current_user, {UserRole.HOST})
    integration = await _get_integration_or_404(session, integration_id)

    if not _is_admin(current_user) and integration.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    if payload.service_type is not None:
        integration.service_type = payload.service_type
    if payload.vendor_name is not None:
        integration.vendor_name = payload.vendor_name
    if payload.auth_method is not None:
        integration.auth_method = payload.auth_method
    if payload.sync_frequency is not None:
        integration.sync_frequency = payload.sync_frequency
    if payload.status is not None:
        integration.status = payload.status
    if payload.metadata is not None:
        integration.metadata_json = payload.metadata
    if payload.kitchen_id is not None:
        integration.kitchen_id = payload.kitchen_id

    await session.commit()
    await session.refresh(integration)

    return _serialize_integration(integration)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    integration = await _get_integration_or_404(session, integration_id)

    if not _is_admin(current_user) and integration.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    await session.delete(integration)
    await session.commit()


