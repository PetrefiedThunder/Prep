"""Pydantic models that back the test data helper API."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserSeed(BaseModel):
    """Payload for idempotently creating a user fixture."""

    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(description="User role name as exposed to the frontend test fixtures.")
    name: str = Field(min_length=1)


class HostMetricsSeed(BaseModel):
    """Payload used to seed the ``mv_host_metrics`` materialized view."""

    host_id: UUID
    revenue_last_30: float = Field(gt=0, description="Revenue total over the previous 30 days.")
    shifts_30: int = Field(ge=0, description="Completed booking count over the previous 30 days.")
    incident_rate: float = Field(
        ge=0, description="Incident rate scored in the materialized view for the previous 30 days."
    )


__all__ = ["HostMetricsSeed", "UserSeed"]
