"""Search endpoints that include compliance-aware filters."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database.connection import get_db

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/kitchens")
async def search_kitchens(
    query: Optional[str] = Query(default=None, description="Free text query"),
    state: Optional[str] = Query(default=None, description="State filter"),
    city: Optional[str] = Query(default=None, description="City filter"),
    equipment: Optional[List[str]] = Query(default=None, description="Required equipment"),
    min_compliance: Optional[str] = Query(default="partial_compliance"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search kitchens with compliance filtering."""

    base_query = """
    SELECT k.*,
           CASE
             WHEN k.compliance_status = 'compliant' THEN 3
             WHEN k.compliance_status = 'partial_compliance' THEN 2
             WHEN k.compliance_status = 'non_compliant' THEN 1
             ELSE 0
           END as compliance_score
    FROM kitchens k
    WHERE 1=1
    """

    params: dict[str, object] = {}

    if state:
        base_query += " AND k.state = :state"
        params["state"] = state.upper()

    if city:
        base_query += " AND k.city = :city"
        params["city"] = city

    if min_compliance == "compliant":
        base_query += " AND k.compliance_status = 'compliant'"
    elif min_compliance == "partial_compliance":
        base_query += " AND k.compliance_status IN ('compliant', 'partial_compliance')"
    elif min_compliance == "non_compliant":
        base_query += " AND k.compliance_status IN ('compliant', 'partial_compliance', 'non_compliant')"

    if equipment:
        for index, item in enumerate(equipment):
            key = f"equipment_{index}"
            base_query += f" AND :{key} = ANY(k.equipment)"
            params[key] = item

    if query:
        base_query += " AND (k.name ILIKE :query OR k.description ILIKE :query)"
        params["query"] = f"%{query}%"

    base_query += " ORDER BY compliance_score DESC, k.created_at DESC"

    result = await db.execute(text(base_query), params)
    kitchens = result.mappings().all()

    return {
        "results": [dict(row) for row in kitchens],
        "filters": {
            "compliance_filter": min_compliance,
            "state": state,
            "city": city,
        },
        "total_count": len(kitchens),
    }
