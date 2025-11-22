"""Administrative regulatory endpoints for dashboards."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from prep.auth import User, require_admin_role
from prep.database.connection import get_db
from prep.regulatory.service import (
    get_scraping_status_snapshot,
    summarize_state_compliance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/regulatory", tags=["admin-regulatory"])


class ScrapeRequest(BaseModel):
    """Request payload to trigger regulatory scraping."""

    states: list[str] = Field(default_factory=list)
    country_code: str = Field(default="US", min_length=2, max_length=2)


@router.get("/states")
async def get_state_regulatory_overview(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),
) -> dict[str, object]:
    """Return aggregated compliance metrics grouped by state.

    SECURITY: Admin-only endpoint - requires admin role.
    """
    # Admin authorization enforced by get_current_admin dependency
    _ = current_admin
    return await summarize_state_compliance(db)


@router.get("/scraping-status")
async def get_scraping_status(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),
) -> dict[str, dict[str, str]]:
    """Return the current scraping status for each state.

    SECURITY: Admin-only endpoint - requires admin role.
    """
    # Admin authorization enforced by get_current_admin dependency
    _ = current_admin
    status = await get_scraping_status_snapshot(db)
    return {"status": status}


@router.post("/scrape")
async def trigger_regulation_scraping(
    payload: ScrapeRequest,
    current_admin: User = Depends(require_admin_role),
) -> dict[str, object]:
    """Schedule scraping for the requested states.

    SECURITY: Admin-only endpoint - requires admin role.
    """
    # Admin authorization enforced by get_current_admin dependency
    _ = current_admin

    if not payload.states:
        raise HTTPException(status_code=400, detail="At least one state must be provided")

    states = [state.upper() for state in payload.states]
    logger.info(
        "Regulatory scraping requested for states: %s by admin: %s", states, current_admin.id
    )
    # In production this would enqueue a background job. For now we acknowledge immediately.
    return {"scheduled": states}
