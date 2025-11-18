"""FastAPI router providing CRUD endpoints for verification tasks."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.database import get_db
from prep.models.orm import VerificationTask, VerificationTaskStatus

from .schemas import (
    VerificationTaskCreate,
    VerificationTaskListResponse,
    VerificationTaskResponse,
    VerificationTaskUpdate,
)

router = APIRouter(prefix="/api/v1/verification-tasks", tags=["verification-tasks"])


SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_task_or_404(session: AsyncSession, task_id: UUID) -> VerificationTask:
    task = await session.get(VerificationTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def _order_query() -> Select[tuple[VerificationTask]]:
    # Order by due date (NULLS LAST) and then by creation time to provide deterministic results.
    return select(VerificationTask).order_by(
        VerificationTask.due_at.is_(None),
        VerificationTask.due_at,
        VerificationTask.created_at,
    )


async def _list_tasks(session: AsyncSession) -> list[VerificationTask]:
    result = await session.execute(_order_query())
    return list(result.scalars().all())


@router.post("", response_model=VerificationTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: VerificationTaskCreate,
    session: SessionDep,
) -> VerificationTaskResponse:
    """Create a new verification task."""

    task = VerificationTask(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        task_type=payload.task_type,
        status=payload.status,
        assigned_to=payload.assigned_to,
        due_at=payload.due_at,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=VerificationTaskListResponse)
async def list_tasks(session: SessionDep) -> VerificationTaskListResponse:
    """Return all verification tasks ordered by due date."""

    tasks = await _list_tasks(session)
    return tasks


@router.get("/{task_id}", response_model=VerificationTaskResponse)
async def get_task(task_id: UUID, session: SessionDep) -> VerificationTaskResponse:
    """Retrieve a single verification task."""

    task = await _get_task_or_404(session, task_id)
    return task


@router.patch("/{task_id}", response_model=VerificationTaskResponse)
async def update_task(
    task_id: UUID,
    payload: VerificationTaskUpdate,
    session: SessionDep,
) -> VerificationTaskResponse:
    """Apply a partial update to a verification task."""

    task = await _get_task_or_404(session, task_id)
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status":
            if value is None:
                continue
            if not isinstance(value, VerificationTaskStatus):
                value = VerificationTaskStatus(value)
            setattr(task, field, value)
            continue
        if field == "task_type":
            if value is None:
                continue
            setattr(task, field, value)
            continue
        if field == "due_at":
            setattr(task, field, value)
            continue
        if field == "assigned_to":
            setattr(task, field, value)
            continue

    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, session: SessionDep) -> Response:
    """Delete a verification task."""

    task = await _get_task_or_404(session, task_id)
    await session.delete(task)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
