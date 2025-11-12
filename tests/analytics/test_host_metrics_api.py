"""Tests for the lightweight host metrics analytics endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.analytics.host_metrics_api import router as host_metrics_router
from prep.database import get_db

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture()
async def app() -> AsyncGenerator[FastAPI, None]:
    """Create a FastAPI app wired with an in-memory database for tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE TABLE mv_host_metrics (
                    host_id TEXT PRIMARY KEY,
                    total_revenue_cents INTEGER,
                    completed_shifts INTEGER,
                    incident_count INTEGER,
                    calculated_at TEXT
                )
                """
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application = FastAPI()
    application.include_router(host_metrics_router)
    application.dependency_overrides[get_db] = _override_get_db
    application.state.session_factory = session_factory

    try:
        yield application
    finally:
        await engine.dispose()


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client targeting the FastAPI test application."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def _seed_metrics(app: FastAPI, **overrides: Any) -> dict[str, Any]:
    """Insert a row into the ``mv_host_metrics`` table for test scenarios."""

    defaults = {
        "host_id": str(uuid4()),
        "total_revenue_cents": 12500,
        "completed_shifts": 14,
        "incident_count": 2,
        "calculated_at": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
    }
    payload = {**defaults, **overrides}

    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO mv_host_metrics (
                    host_id,
                    total_revenue_cents,
                    completed_shifts,
                    incident_count,
                    calculated_at
                ) VALUES (:host_id, :total_revenue_cents, :completed_shifts, :incident_count, :calculated_at)
                """
            ),
            payload,
        )
        await session.commit()

    return payload


async def test_get_host_metrics_returns_structured_payload(
    app: FastAPI, client: AsyncClient
) -> None:
    """The endpoint should return structured metrics data when available."""

    metrics = await _seed_metrics(app)
    response = await client.get(f"/analytics/host/{metrics['host_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "host_id": metrics["host_id"],
        "data_available": True,
        "metrics": {
            "total_revenue_cents": metrics["total_revenue_cents"],
            "completed_shifts": metrics["completed_shifts"],
            "incident_count": metrics["incident_count"],
        },
        "calculated_at": metrics["calculated_at"],
    }


async def test_get_host_metrics_handles_missing_rows(client: AsyncClient) -> None:
    """Requests for hosts without metrics should return safe defaults."""

    missing_host_id = uuid4()
    response = await client.get(f"/analytics/host/{missing_host_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "host_id": str(missing_host_id),
        "data_available": False,
        "metrics": {
            "total_revenue_cents": 0,
            "completed_shifts": 0,
            "incident_count": 0,
        },
        "calculated_at": None,
    }
