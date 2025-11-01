"""Debug utilities exposed only in staging environments."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db
from prep.models.orm import Kitchen, StripeWebhookEvent, User, UserRole
from prep.settings import get_settings

router = APIRouter(prefix="/debug", tags=["debug"])


def require_staging(settings=Depends(get_settings)) -> Any:
    """Ensure debug routes are accessible only in staging deployments."""

    if settings.environment.lower() != "staging":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return settings


@router.get("/random_maker")
async def random_maker(
    _: Any = Depends(require_staging),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    stmt = (
        select(User.id)
        .where(User.role.in_([UserRole.CUSTOMER, UserRole.FOOD_BUSINESS_ADMIN]))
        .order_by(func.random())
        .limit(1)
    )
    result = await db.execute(stmt)
    maker_id = result.scalar_one_or_none()
    if maker_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No makers available")
    return {"maker_id": str(maker_id)}


@router.get("/random_kitchen")
async def random_kitchen(
    _: Any = Depends(require_staging),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    stmt = select(Kitchen.id).order_by(func.random()).limit(1)
    result = await db.execute(stmt)
    kitchen_id = result.scalar_one_or_none()
    if kitchen_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No kitchens available")
    return {"kitchen_id": str(kitchen_id)}


@router.get("/webhook_count")
async def webhook_count(
    event_id: str = Query(..., min_length=1),
    _: Any = Depends(require_staging),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    stmt = select(func.count(StripeWebhookEvent.id)).where(StripeWebhookEvent.event_id == event_id)
    result = await db.execute(stmt)
    count = result.scalar_one()
    return {"event_id": event_id, "count": int(count or 0)}
