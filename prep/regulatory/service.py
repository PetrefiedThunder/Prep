"""Regulatory data helpers shared across API modules."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import case, func, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models import Kitchen

REGULATORY_ALERT_WINDOW_DAYS = 30


async def get_regulations_for_jurisdiction(
    db: AsyncSession,
    state: Optional[str],
    city: Optional[str] = None,
    *,
    country_code: str = "US",
    state_province: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Return regulatory updates for the given jurisdiction."""

    if not state:
        return []

    stmt = text(
        """
        SELECT state, city, regulation_type, change_description, effective_date, created_at
        FROM regulatory_updates
        WHERE state = :state
          AND (:city IS NULL OR city IS NULL OR city = :city)
        ORDER BY effective_date DESC NULLS LAST, created_at DESC
        LIMIT 25
        """
    )
    normalized_country = (country_code or "US").upper()
    province = state_province or (state.upper() if state else None)
    result = await db.execute(stmt, {"state": state.upper(), "city": city})
    rows = result.mappings().all()

    regulations: List[Dict[str, str]] = []
    for row in rows:
        regulations.append(
            {
                "title": f"{row.get('regulation_type', 'Regulation Update')}" if row.get("regulation_type") else "Regulation Update",
                "description": row.get("change_description", "Updated regulatory guidance."),
                "jurisdiction": _format_jurisdiction(row),
                "regulation_type": row.get("regulation_type", "general"),
                "effective_date": _format_date(row.get("effective_date")),
                "guidance": row.get("change_description"),
                "country_code": normalized_country,
                "state_province": province,
                "city": row.get("city"),
            }
        )

    if not regulations:
        regulations.append(
            {
                "title": "Food safety compliance checklist",
                "description": "Maintain active permits, document recent inspections, and upload insurance certificates.",
                "jurisdiction": _format_fallback_jurisdiction(state, city),
                "regulation_type": "general",
                "effective_date": None,
                "guidance": "Schedule a compliance review and ensure all documents are uploaded.",
                "country_code": normalized_country,
                "state_province": province,
                "city": city,
            }
        )

    return regulations


async def summarize_state_compliance(db: AsyncSession) -> Dict[str, object]:
    """Aggregate compliance stats grouped by state."""

    status_case = case(
        (Kitchen.compliance_status == "compliant", 1),
        else_=0,
    )
    non_compliant_case = case(
        (Kitchen.compliance_status == "non_compliant", 1),
        else_=0,
    )

    stmt = (
        select(
            func.upper(Kitchen.state).label("state"),
            func.count(Kitchen.id).label("total_kitchens"),
            func.sum(status_case).label("compliant_kitchens"),
            func.sum(non_compliant_case).label("non_compliant_kitchens"),
        )
        .where(Kitchen.state.isnot(None))
        .group_by(func.upper(Kitchen.state))
        .order_by(func.upper(Kitchen.state))
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()

    states: List[Dict[str, object]] = []
    total_kitchens = 0
    compliant_kitchens = 0
    non_compliant_kitchens = 0

    for row in rows:
        total_kitchens += row["total_kitchens"] or 0
        compliant_kitchens += row["compliant_kitchens"] or 0
        non_compliant_kitchens += row["non_compliant_kitchens"] or 0

        states.append(
            {
                "code": row["state"],
                "name": row["state"],
                "total_kitchens": row["total_kitchens"] or 0,
                "compliant_kitchens": row["compliant_kitchens"] or 0,
                "non_compliant_kitchens": row["non_compliant_kitchens"] or 0,
            }
        )

    alerts = await get_regulatory_alerts(db)

    return {
        "total_kitchens": total_kitchens,
        "compliant_kitchens": compliant_kitchens,
        "non_compliant_kitchens": non_compliant_kitchens,
        "states_covered": len(states),
        "states": states,
        "alerts": alerts,
    }


async def get_regulatory_alerts(db: AsyncSession) -> List[Dict[str, str]]:
    """Return regulatory alerts with upcoming effective dates."""

    window_start = datetime.utcnow()
    window_end = window_start + timedelta(days=REGULATORY_ALERT_WINDOW_DAYS)
    stmt = text(
        """
        SELECT state, city, regulation_type, change_description, effective_date
        FROM regulatory_updates
        WHERE effective_date BETWEEN :start AND :end
        ORDER BY effective_date ASC
        LIMIT 50
        """
    )
    result = await db.execute(stmt, {"start": window_start, "end": window_end})
    rows = result.mappings().all()

    alerts: List[Dict[str, str]] = []
    for row in rows:
        message = row.get("change_description") or "Regulatory update"
        alerts.append(
            {
                "message": message,
                "state": _format_jurisdiction(row),
                "regulation_type": row.get("regulation_type"),
                "effective_date": _format_date(row.get("effective_date")),
            }
        )
    return alerts


async def get_scraping_status_snapshot(db: AsyncSession) -> Dict[str, str]:
    """Return a best-effort scraping status per state."""

    stmt = text(
        """
        SELECT state, MAX(created_at) AS last_run
        FROM regulatory_updates
        GROUP BY state
        """
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()

    status: Dict[str, str] = {}
    now = datetime.utcnow()
    for row in rows:
        last_run = row.get("last_run")
        if last_run is None:
            status[row["state"]] = "idle"
            continue
        delta = now - last_run
        if delta <= timedelta(hours=1):
            status[row["state"]] = "running"
        elif delta <= timedelta(days=7):
            status[row["state"]] = "recent"
        else:
            status[row["state"]] = "idle"
    return status


def _format_jurisdiction(row: RowMapping) -> str:
    state = row.get("state")
    city = row.get("city")
    if city:
        return f"{city}, {state}"
    if state:
        return state
    return "United States"


def _format_fallback_jurisdiction(state: Optional[str], city: Optional[str]) -> str:
    if city and state:
        return f"{city}, {state.upper()}"
    if state:
        return state.upper()
    return "United States"


def _format_date(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    try:
        return datetime.fromisoformat(str(value)).date().isoformat()
    except ValueError:
        return str(value)


__all__ = [
    "get_regulations_for_jurisdiction",
    "summarize_state_compliance",
    "get_regulatory_alerts",
    "get_scraping_status_snapshot",
]
