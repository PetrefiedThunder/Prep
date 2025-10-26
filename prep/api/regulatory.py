"""Public regulatory endpoints used by the Prep client."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db
from prep.regulatory.service import get_regulations_for_jurisdiction

router = APIRouter(prefix="/regulatory", tags=["regulatory"])


@router.get("/regulations/{state}")
async def list_regulations(
    state: str,
    city: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return regulations for the provided jurisdiction."""

    regulations = await get_regulations_for_jurisdiction(db, state, city)
    return {"regulations": regulations}
