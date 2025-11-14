"""Schemas powering external rating integrations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ExternalCategory(BaseModel):
    """Category entry returned by external providers."""

    alias: str
    title: str


class ExternalBusiness(BaseModel):
    """Simplified external business representation."""

    id: str
    name: str
    source: str
    url: HttpUrl | None = None
    phone: str | None = None
    address: list[str] = Field(default_factory=list)
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rating: float | None = None
    review_count: int | None = None
    price: str | None = None
    categories: list[ExternalCategory] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalBusinessDetails(ExternalBusiness):
    """Detailed external business record including extended metadata."""

    photos: list[HttpUrl] = Field(default_factory=list)
    hours: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExternalBusinessReview(BaseModel):
    """Review content returned by an external provider."""

    id: str
    source: str
    author: str | None = None
    rating: float | None = None
    text: str | None = None
    language: str | None = None
    url: HttpUrl | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalBusinessSearchResponse(BaseModel):
    """Envelope returned for a business search operation."""

    businesses: list[ExternalBusiness]
    total: int
    context: dict[str, Any] = Field(default_factory=dict)


class ExternalReviewListResponse(BaseModel):
    """Envelope returned when fetching external reviews."""

    business_id: str
    source: str
    reviews: list[ExternalBusinessReview]
    total: int


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
    external_count: int = 0


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


class RatingTrendPoint(BaseModel):
    """Time series point representing a rating snapshot."""

    source: str
    rating: float | None
    rating_scale: float
    rating_count: int | None = None
    normalized_rating: float | None = None
    captured_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class KitchenRatingHistoryResponse(BaseModel):
    """Rating history timeline for a kitchen."""

    kitchen_id: UUID
    points: list[RatingTrendPoint]


class SentimentReviewInput(BaseModel):
    """Single review text submitted for sentiment analysis."""

    review_id: UUID | None = None
    kitchen_id: UUID | None = None
    source: str | None = None
    rating: float | None = Field(default=None, ge=0)
    text: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SentimentAnalysisRequest(BaseModel):
    """Payload for triggering a sentiment analysis run."""

    kitchen_id: UUID | None = None
    source: str | None = None
    reviews: list[SentimentReviewInput]


class SentimentAnalysisResponse(BaseModel):
    """Aggregated sentiment results for a batch of reviews."""

    kitchen_id: UUID | None
    source: str | None
    average_score: float
    label: str
    review_count: int
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    keywords: list[str] = Field(default_factory=list)
    generated_at: datetime


class SentimentTrendPoint(BaseModel):
    """Historical sentiment entry for reporting."""

    kitchen_id: UUID | None
    source: str | None
    window_start: datetime
    window_end: datetime
    average_score: float
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    sample_size: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class SentimentTrendResponse(BaseModel):
    """Sentiment trend report."""

    kitchen_id: UUID | None
    source: str | None
    points: list[SentimentTrendPoint]
    generated_at: datetime


__all__ = [
    "ExternalBusiness",
    "ExternalBusinessDetails",
    "ExternalBusinessReview",
    "ExternalBusinessSearchResponse",
    "ExternalCategory",
    "ExternalRatingModel",
    "ExternalRatingSyncItem",
    "ExternalRatingSyncRequest",
    "ExternalRatingSyncResponse",
    "ExternalReviewListResponse",
    "KitchenRatingHistoryResponse",
    "KitchenRatingResponse",
    "RatingTrendPoint",
    "SentimentAnalysisRequest",
    "SentimentAnalysisResponse",
    "SentimentReviewInput",
    "SentimentTrendPoint",
    "SentimentTrendResponse",
]
