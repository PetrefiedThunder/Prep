"""FastAPI router that powers the Playwright test data helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import SelectStatement, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db
from prep.models.orm import User, UserRole
from prep.platform.security import hash_password

from .schemas import HostMetricsSeed, UserSeed

router = APIRouter(prefix="/api/test-data", tags=["test-data"])


_ROLE_ALIASES: Mapping[str, UserRole] = {
    "admin": UserRole.ADMIN,
    "host": UserRole.HOST,
    "renter": UserRole.CUSTOMER,
    "customer": UserRole.CUSTOMER,
    "guest": UserRole.CUSTOMER,
    "compliance": UserRole.ADMIN,
}


def _normalize_role(raw_role: str) -> UserRole:
    try:
        return _ROLE_ALIASES[raw_role.lower()]
    except KeyError as exc:  # pragma: no cover - defensive guard for new roles
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported role '{raw_role}' for test data provisioning.",
        ) from exc


@router.post("/users")
async def ensure_user(payload: UserSeed, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Create or update a user fixture for automated tests."""

    role = _normalize_role(payload.role)
    stmt: SelectStatement[tuple[User]] = select(User).where(User.email == payload.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    hashed_password = hash_password(payload.password)

    if user is None:
        user = User(
            email=payload.email, full_name=payload.name, role=role, hashed_password=hashed_password
        )
        session.add(user)
    else:
        user.full_name = payload.name
        user.role = role
        user.hashed_password = hashed_password
        user.is_active = True
        user.is_suspended = False
        user.suspension_reason = None

    try:
        await session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - surface deterministic error
        await session.rollback()
        raise HTTPException(status_code=500, detail="Unable to persist test user fixture") from exc

    await session.refresh(user)
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "name": user.full_name,
    }


async def _fetch_mv_host_metrics_columns(session: AsyncSession) -> set[str]:
    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'mv_host_metrics'
        """
    )
    result = await session.execute(query)
    return {row[0] for row in result}


@router.post("/host-metrics")
async def seed_host_metrics(
    payload: HostMetricsSeed, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Upsert rows into the ``mv_host_metrics`` materialized view for deterministic tests."""

    columns = await _fetch_mv_host_metrics_columns(session)

    params: dict[str, Any]
    if {"revenue_last_30", "shifts_30", "incident_rate", "calculated_at"}.issubset(columns):
        params = {
            "host_id": str(payload.host_id),
            "revenue_last_30": payload.revenue_last_30,
            "shifts_30": payload.shifts_30,
            "incident_rate": payload.incident_rate,
        }
        upsert_query = text(
            """
            INSERT INTO mv_host_metrics (host_id, revenue_last_30, shifts_30, incident_rate, calculated_at)
            VALUES (:host_id, :revenue_last_30, :shifts_30, :incident_rate, NOW())
            ON CONFLICT (host_id) DO UPDATE
            SET revenue_last_30 = EXCLUDED.revenue_last_30,
                shifts_30 = EXCLUDED.shifts_30,
                incident_rate = EXCLUDED.incident_rate,
                calculated_at = NOW()
            """
        )
    elif {"total_revenue_cents", "completed_shifts", "incident_count", "calculated_at"}.issubset(
        columns
    ):
        params = {
            "host_id": str(payload.host_id),
            "total_revenue_cents": int(round(payload.revenue_last_30 * 100)),
            "completed_shifts": payload.shifts_30,
            "incident_count": max(0, int(round(payload.incident_rate * 100))),
        }
        upsert_query = text(
            """
            INSERT INTO mv_host_metrics (host_id, total_revenue_cents, completed_shifts, incident_count, calculated_at)
            VALUES (:host_id, :total_revenue_cents, :completed_shifts, :incident_count, NOW())
            ON CONFLICT (host_id) DO UPDATE
            SET total_revenue_cents = EXCLUDED.total_revenue_cents,
                completed_shifts = EXCLUDED.completed_shifts,
                incident_count = EXCLUDED.incident_count,
                calculated_at = NOW()
            """
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="mv_host_metrics view is missing expected columns for seeding",
        )

    try:
        await session.execute(upsert_query, params)
        await session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - deterministic error surfacing
        await session.rollback()
        raise HTTPException(status_code=500, detail="Unable to seed host metrics fixture") from exc

    return {"host_id": str(payload.host_id)}


__all__ = ["router", "ensure_user", "seed_host_metrics"]
