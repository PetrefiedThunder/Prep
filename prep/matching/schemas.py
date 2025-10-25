"""Pydantic models powering the smart matching API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PreferenceSettings(BaseModel):
    """User-configurable matching preferences."""

    equipment: list[str] = Field(default_factory=list, description="Required kitchen equipment")
    certifications: list[str] = Field(
        default_factory=list, description="Required certification levels"
    )
    cuisines: list[str] = Field(
        default_factory=list, description="Preferred cuisine styles"
    )
    preferred_cities: list[str] = Field(default_factory=list)
    preferred_states: list[str] = Field(default_factory=list)
    availability: list[str] = Field(default_factory=list, description="Desired availability patterns")
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    max_distance_km: float | None = Field(default=None, ge=0)


class UserPreferenceModel(PreferenceSettings):
    """Persisted preference response."""

    user_id: UUID
    updated_at: datetime


class KitchenMatchRequest(BaseModel):
    """Request payload for computing kitchen matches."""

    limit: int = Field(default=10, ge=1, le=50)
    preferences: PreferenceSettings | None = Field(
        default=None,
        description="Optional override preferences for a one-off match run",
    )


class MatchReason(BaseModel):
    """Explains why a kitchen was recommended."""

    criterion: str
    summary: str
    weight: float
    contribution: float


class KitchenMatchModel(BaseModel):
    """Single kitchen recommendation entry."""

    kitchen_id: UUID
    kitchen_name: str
    city: str | None = None
    state: str | None = None
    hourly_rate: float | None = None
    trust_score: float | None = None
    score: float
    confidence: float
    reasons: list[MatchReason]
    cuisines: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    availability: list[str] = Field(default_factory=list)
    external_rating: float | None = None
    popularity_index: float | None = None
    demand_forecast: float | None = None

    model_config = {
        "from_attributes": True,
    }


class MatchResponse(BaseModel):
    """Response for kitchen matching operations."""

    matches: list[KitchenMatchModel]
    generated_at: datetime
    preferences: PreferenceSettings | None


class ExternalRatingModel(BaseModel):
    """External rating source payload."""

    source: str
    rating: float
    rating_scale: float
    rating_count: int | None = None
    normalized_rating: float | None = None
    url: HttpUrl | None = None
    synced_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class KitchenRatingResponse(BaseModel):
    """Aggregated rating information for a kitchen."""

    kitchen_id: UUID
    internal_average: float | None
    internal_count: int
    external_sources: list[ExternalRatingModel]
    normalized_score: float | None


class ExternalRatingSyncItem(BaseModel):
    """Incoming external rating entry."""

    kitchen_id: UUID
    source: str
    rating: float = Field(ge=0)
    rating_scale: float = Field(default=5, gt=0)
    rating_count: int | None = Field(default=None, ge=0)
    url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalRatingSyncRequest(BaseModel):
    """Request body for syncing external ratings."""

    sources: list[ExternalRatingSyncItem]


class ExternalRatingSyncResponse(BaseModel):
    """Response returned after syncing external ratings."""

    updated: int
    sources: list[ExternalRatingModel]
