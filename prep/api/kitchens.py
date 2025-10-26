"""Kitchen management API endpoints."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db
from prep.models import Kitchen

router = APIRouter(prefix="/kitchens", tags=["kitchens"])


class KitchenCreate(BaseModel):
    """Payload used to create a kitchen listing."""

    name: str
    address: str
    description: str
    pricing: dict
    equipment: List[str]


class KitchenResponse(KitchenCreate):
    """Kitchen representation returned by the API."""

    id: str
    host_id: str
    created_at: str


@router.post("/", response_model=KitchenResponse, status_code=status.HTTP_201_CREATED)
async def create_kitchen(
    kitchen_data: KitchenCreate,
    db: AsyncSession = Depends(get_db),
) -> KitchenResponse:
    """Create a new kitchen listing."""

    host_id = uuid.uuid4()

    new_kitchen = Kitchen(
        name=kitchen_data.name,
        host_id=host_id,
        address=kitchen_data.address,
        description=kitchen_data.description,
        pricing=kitchen_data.pricing,
        equipment=kitchen_data.equipment,
    )

    db.add(new_kitchen)
    await db.commit()
    await db.refresh(new_kitchen)

    return KitchenResponse(
        id=str(new_kitchen.id),
        host_id=str(new_kitchen.host_id),
        name=new_kitchen.name,
        address=new_kitchen.address,
        description=new_kitchen.description,
        pricing=new_kitchen.pricing,
        equipment=new_kitchen.equipment,
        created_at=new_kitchen.created_at.isoformat(),
    )


@router.get("/{kitchen_id}", response_model=KitchenResponse)
async def get_kitchen(kitchen_id: str, db: AsyncSession = Depends(get_db)) -> KitchenResponse:
    """Retrieve a specific kitchen by its identifier."""

    try:
        kitchen_uuid = uuid.UUID(kitchen_id)
    except ValueError as exc:  # pragma: no cover - validation guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kitchen ID") from exc

    result = await db.execute(select(Kitchen).where(Kitchen.id == kitchen_uuid))
    kitchen = result.scalar_one_or_none()
    if not kitchen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

    return KitchenResponse(
        id=str(kitchen.id),
        host_id=str(kitchen.host_id),
        name=kitchen.name,
        address=kitchen.address,
        description=kitchen.description,
        pricing=kitchen.pricing,
        equipment=kitchen.equipment,
        created_at=kitchen.created_at.isoformat(),
    )


@router.get("/", response_model=List[KitchenResponse])
async def list_kitchens(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[KitchenResponse]:
    """List kitchens with pagination support."""

    result = await db.execute(select(Kitchen).offset(skip).limit(limit))
    kitchens = result.scalars().all()

    return [
        KitchenResponse(
            id=str(kitchen.id),
            host_id=str(kitchen.host_id),
            name=kitchen.name,
            address=kitchen.address,
            description=kitchen.description,
            pricing=kitchen.pricing,
            equipment=kitchen.equipment,
            created_at=kitchen.created_at.isoformat(),
        )
        for kitchen in kitchens
    ]
