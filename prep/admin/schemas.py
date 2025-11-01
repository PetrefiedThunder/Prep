"""Pydantic schemas for the admin dashboard API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prep.models.db import CertificationReviewStatus, ModerationStatus


class PaginationMeta(BaseModel):
    """Metadata describing a paginated response."""

    limit: int = Field(default=20, ge=1, le=100)
    cursor: datetime | None = Field(
        default=None,
        description="Cursor supplied by the client for this page",
    )
    next_cursor: datetime | None = Field(
        default=None,
        description="Cursor to fetch the next page of data",
    )
    total: int = Field(ge=0)


class KitchenSummary(BaseModel):
    """Summary information for a kitchen awaiting moderation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    owner_email: str
    owner_name: str
    location: str
    submitted_at: datetime
    moderation_status: ModerationStatus
    certification_status: CertificationReviewStatus
    trust_score: Optional[Decimal]
    hourly_rate: Optional[Decimal]
    moderated_at: Optional[datetime]


class KitchenDetail(KitchenSummary):
    """Expanded kitchen details for review."""

    description: Optional[str]
    rejection_reason: Optional[str]
    certifications: List["CertificationSummary"] = Field(default_factory=list)


class CertificationSummary(BaseModel):
    """Serialized certification information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kitchen_id: UUID
    kitchen_name: str
    document_type: str
    document_url: str
    status: CertificationReviewStatus
    submitted_at: datetime
    verified_at: Optional[datetime]
    reviewer_id: Optional[UUID]
    rejection_reason: Optional[str]
    expires_at: Optional[datetime]


class ModerationDecision(str, Enum):
    """Possible moderation actions that an admin can take."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class ModerationRequest(BaseModel):
    """Request body for moderating a kitchen."""

    action: ModerationDecision = Field(description="Target moderation action for the kitchen")
    reason: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=500)


class ModerationResponse(BaseModel):
    """Response payload for a moderation action."""

    kitchen: KitchenDetail
    message: str


class CertificationDecisionRequest(BaseModel):
    """Payload for verifying or rejecting a certification document."""

    approve: bool = Field(description="Whether to approve the document")
    rejection_reason: Optional[str] = Field(default=None, max_length=500)


class CertificationDecisionResponse(BaseModel):
    """Response payload after verifying a certification."""

    certification: CertificationSummary
    message: str


class KitchenModerationStats(BaseModel):
    """Aggregated moderation metrics."""

    total: int
    pending: int
    approved: int
    rejected: int
    changes_requested: int
    approvals_last_7_days: int


class CertificationStats(BaseModel):
    """Aggregated certification metrics."""

    total: int
    pending: int
    approved: int
    rejected: int
    expiring_soon: int


class UserSummary(BaseModel):
    """Serialized information about a user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_suspended: bool
    suspension_reason: Optional[str]
    created_at: datetime
    last_login_at: Optional[datetime]


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: List[UserSummary]
    pagination: PaginationMeta


class UserStats(BaseModel):
    """User metrics surfaced to admins."""

    total: int
    active: int
    suspended: int
    admins: int
    hosts: int


class SuspendUserRequest(BaseModel):
    """Payload used to suspend a user."""

    reason: Optional[str] = Field(default=None, max_length=250)


class CertificationListResponse(BaseModel):
    """Paginated certification document response."""

    items: List[CertificationSummary]
    pagination: PaginationMeta


class KitchenListResponse(BaseModel):
    """Paginated kitchen moderation response."""

    items: List[KitchenSummary]
    pagination: PaginationMeta


class ChecklistTemplateCreateRequest(BaseModel):
    """Payload for creating a new checklist template version."""

    name: str = Field(min_length=1, max_length=120)
    schema: dict[str, Any] = Field(description="JSON schema describing the checklist fields")
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "ChecklistTemplateCreateRequest":
        if not self.schema:
            raise ValueError("schema cannot be empty")
        if "type" not in self.schema:
            raise ValueError("schema must include a 'type' field")
        return self


class ChecklistTemplateResponse(BaseModel):
    """Serialized representation of a stored checklist template version."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: int
    schema: dict[str, Any]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
