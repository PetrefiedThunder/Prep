"""Pydantic schemas for the review and rating system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from prep.models.orm import ReviewFlagStatus, ReviewStatus


class RatingBreakdown(BaseModel):
    """Detailed rating values for a review."""

    equipment: float = Field(ge=1, le=5)
    cleanliness: float = Field(ge=1, le=5)
    communication: float = Field(ge=1, le=5)
    value: float = Field(ge=1, le=5)


class ReviewSubmissionRequest(BaseModel):
    """Payload submitted when a guest leaves a review."""

    booking_id: UUID
    kitchen_id: UUID
    overall_rating: float = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    ratings: RatingBreakdown | None = None


class ReviewPhotoCreate(BaseModel):
    """Request body for attaching an existing asset to a review."""

    url: HttpUrl = Field(description="Publicly accessible URL for the review photo")
    caption: str | None = Field(default=None, max_length=255)


class HostResponseUpdate(BaseModel):
    """Host response body for a review."""

    response: str = Field(..., max_length=2000)


class ReviewVoteRequest(BaseModel):
    """Payload for registering a helpfulness vote."""

    helpful: bool = Field(description="Whether the review was helpful to the voter")


class ReviewFlagRequest(BaseModel):
    """Body used when flagging a review for moderation."""

    reason: str = Field(..., max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class ReviewModerationRequest(BaseModel):
    """Admin payload for approving or rejecting a review."""

    action: Literal["approve", "reject"]
    notes: str | None = Field(default=None, max_length=2000)


class ReviewPhotoModel(BaseModel):
    """Serialized representation of a review photo."""

    id: UUID
    url: str
    caption: str | None
    uploaded_at: datetime

    model_config = {
        "from_attributes": True,
    }


class RatingAggregate(BaseModel):
    """Aggregated rating data for a kitchen."""

    total_reviews: int = 0
    average_rating: float = 0
    average_equipment: float = 0
    average_cleanliness: float = 0
    average_communication: float = 0
    average_value: float = 0


class ReviewModel(BaseModel):
    """Representation of a review returned to clients."""

    id: UUID
    booking_id: UUID
    kitchen_id: UUID
    host_id: UUID
    customer_id: UUID
    rating: float
    ratings: RatingBreakdown
    comment: str | None
    status: ReviewStatus
    spam_score: float
    helpful_count: int
    created_at: datetime
    updated_at: datetime
    host_response: str | None
    host_response_at: datetime | None
    photos: list[ReviewPhotoModel]

    model_config = {
        "from_attributes": True,
    }


class ReviewListResponse(BaseModel):
    """Response envelope for review listing endpoints."""

    items: list[ReviewModel]
    aggregate: RatingAggregate


class ReviewFlagModel(BaseModel):
    """Representation of a review flag record."""

    id: UUID
    reporter_id: UUID
    reason: str
    notes: str | None
    status: ReviewFlagStatus
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class UserReviewListResponse(BaseModel):
    """Response model for a user's review history."""

    items: list[ReviewModel]
    pending_flags: list[ReviewFlagModel]
