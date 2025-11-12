"""Integration tests for the verification task FastAPI router."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.database import get_db
from prep.models.orm import (
    Base,
    User,
    UserRole,
    VerificationTask,
    VerificationTaskStatus,
)
from prep.verification_tasks.api import router as verification_tasks_router


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    application = FastAPI()
    application.include_router(verification_tasks_router)
    application.state.session_factory = session_factory

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = _override_get_db

    try:
        yield application
    finally:
        await engine.dispose()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


async def _create_user(app: FastAPI, *, email: str) -> User:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        user = User(email=email, full_name="Admin User", role=UserRole.ADMIN)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.anyio("asyncio")
async def test_create_task(client: AsyncClient, app: FastAPI) -> None:
    assignee = await _create_user(app, email="assignee@example.com")
    due_at = datetime.now(UTC) + timedelta(days=2)

    response = await client.post(
        "/api/v1/verification-tasks",
        json={
            "entity_type": "kitchen",
            "entity_id": str(uuid4()),
            "task_type": "license_review",
            "status": VerificationTaskStatus.IN_PROGRESS.value,
            "assigned_to": str(assignee.id),
            "due_at": due_at.isoformat(),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == VerificationTaskStatus.IN_PROGRESS.value
    assert data["assigned_to"] == str(assignee.id)
    assert data["task_type"] == "license_review"
    assert data["entity_type"] == "kitchen"

    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        task = await session.get(VerificationTask, UUID(data["id"]))
        assert task is not None
        assert task.status is VerificationTaskStatus.IN_PROGRESS


@pytest.mark.anyio("asyncio")
async def test_list_tasks_orders_by_due_date(client: AsyncClient, app: FastAPI) -> None:
    await client.post(
        "/api/v1/verification-tasks",
        json={
            "entity_type": "kitchen",
            "entity_id": str(uuid4()),
            "task_type": "document_upload",
            "due_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        },
    )
    await client.post(
        "/api/v1/verification-tasks",
        json={
            "entity_type": "user",
            "entity_id": str(uuid4()),
            "task_type": "background_check",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    response = await client.get("/api/v1/verification-tasks")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2

    first_due = datetime.fromisoformat(items[0]["due_at"])
    second_due = datetime.fromisoformat(items[1]["due_at"])
    assert first_due <= second_due


@pytest.mark.anyio("asyncio")
async def test_update_task_allows_assignment_and_completion(
    client: AsyncClient, app: FastAPI
) -> None:
    creator = await _create_user(app, email="creator@example.com")
    task_response = await client.post(
        "/api/v1/verification-tasks",
        json={
            "entity_type": "kitchen",
            "entity_id": str(uuid4()),
            "task_type": "inspection_follow_up",
            "assigned_to": str(creator.id),
        },
    )
    task_response.raise_for_status()
    task_id = task_response.json()["id"]

    new_assignee = await _create_user(app, email="reviewer@example.com")

    response = await client.patch(
        f"/api/v1/verification-tasks/{task_id}",
        json={
            "status": VerificationTaskStatus.COMPLETED.value,
            "assigned_to": str(new_assignee.id),
            "due_at": None,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == VerificationTaskStatus.COMPLETED.value
    assert payload["assigned_to"] == str(new_assignee.id)
    assert payload["due_at"] is None

    detail = await client.get(f"/api/v1/verification-tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == VerificationTaskStatus.COMPLETED.value


@pytest.mark.anyio("asyncio")
async def test_delete_task_removes_record(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/verification-tasks",
        json={
            "entity_type": "kitchen",
            "entity_id": str(uuid4()),
            "task_type": "follow_up_call",
        },
    )
    create_response.raise_for_status()
    task_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/verification-tasks/{task_id}")
    assert response.status_code == 204

    not_found = await client.get(f"/api/v1/verification-tasks/{task_id}")
    assert not_found.status_code == 404
