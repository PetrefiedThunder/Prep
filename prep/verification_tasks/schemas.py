"""Pydantic schemas for verification task endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from prep.models.orm import VerificationTaskStatus


class VerificationTaskCreate(BaseModel):
    """Payload for creating a new verification task."""

    entity_type: str = Field(..., max_length=100)
    entity_id: UUID
    task_type: str = Field(..., max_length=100)
    status: VerificationTaskStatus = Field(
        default=VerificationTaskStatus.PENDING,
        description="Initial status for the verification task.",
    )
    assigned_to: UUID | None = Field(
        default=None,
        description="Optional identifier of the user responsible for the task.",
    )
    due_at: datetime | None = Field(
        default=None,
        description="Optional due date for completing the task.",
    )


class VerificationTaskUpdate(BaseModel):
    """Payload for partially updating a verification task."""

    status: VerificationTaskStatus | None = None
    assigned_to: UUID | None = Field(default=None, description="Reassign the task")
    due_at: datetime | None = Field(default=None, description="Update the due date")
    task_type: str | None = Field(
        default=None,
        max_length=100,
        description="Optionally update the task category.",
    )


class VerificationTaskResponse(BaseModel):
    """API representation of a verification task."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    task_type: str
    status: VerificationTaskStatus
    assigned_to: UUID | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime


VerificationTaskListResponse = list[VerificationTaskResponse]

__all__ = [
    "VerificationTaskCreate",
    "VerificationTaskUpdate",
    "VerificationTaskResponse",
    "VerificationTaskListResponse",
]
