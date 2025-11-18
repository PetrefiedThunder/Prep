"""Tests for certification API authentication and authorization."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.admin.certification_api import certification_router
from prep.database import get_db
from prep.models.db import Base, User, UserRole


@pytest.fixture(autouse=True)
def _set_admin_jwt_secret() -> None:
    """Ensure ADMIN_JWT_SECRET is set for all tests in this module."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret-key-for-testing-purposes-only"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"


@pytest.fixture()
async def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
async def session_factory(engine):
    """Create a session factory for the test database."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture()
async def app(session_factory) -> AsyncGenerator[FastAPI, None]:
    """Create a FastAPI test application with certification router."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application = FastAPI()
    application.include_router(certification_router)
    application.dependency_overrides[get_db] = _override_get_db

    yield application


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture()
async def admin_user(session_factory) -> User:
    """Create an admin user in the database."""
    async with session_factory() as session:
        admin = User(
            id=uuid4(),
            email="admin@example.com",
            full_name="Test Admin",
            hashed_password="hashed",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin


@pytest.fixture()
async def regular_user(session_factory) -> User:
    """Create a regular (non-admin) user in the database."""
    async with session_factory() as session:
        user = User(
            id=uuid4(),
            email="user@example.com",
            full_name="Regular User",
            hashed_password="hashed",
            role=UserRole.HOST,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _create_admin_token(admin_id: UUID, permissions: list[str] | None = None) -> str:
    """Create a valid admin JWT token."""
    secret = os.getenv("ADMIN_JWT_SECRET", "test-admin-secret-key-for-testing-purposes-only")
    audience = os.getenv("ADMIN_JWT_AUDIENCE", "prep-admin")

    payload = {
        "sub": str(admin_id),
        "aud": audience,
        "permissions": permissions or ["certifications:verify"],
    }

    return jwt.encode(payload, secret, algorithm="HS256")


async def test_list_pending_certifications_without_auth(client: AsyncClient) -> None:
    """Verify that unauthenticated requests to list pending certifications are rejected."""

    response = await client.get("/api/v1/admin/certifications/pending")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


async def test_list_pending_certifications_with_invalid_token(client: AsyncClient) -> None:
    """Verify that requests with invalid tokens are rejected."""

    response = await client.get(
        "/api/v1/admin/certifications/pending",
        headers={"Authorization": "Bearer invalid-token-here"},
    )

    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]


async def test_list_pending_certifications_with_regular_user_token(
    client: AsyncClient, regular_user: User
) -> None:
    """Verify that non-admin users cannot access certification endpoints."""

    token = _create_admin_token(regular_user.id)

    response = await client.get(
        "/api/v1/admin/certifications/pending",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin not authorized"


async def test_list_pending_certifications_with_valid_admin_token(
    client: AsyncClient, admin_user: User
) -> None:
    """Verify that authenticated admin users can access certification endpoints."""

    token = _create_admin_token(admin_user.id)

    response = await client.get(
        "/api/v1/admin/certifications/pending",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "certifications" in data
    assert "total_count" in data
    assert isinstance(data["certifications"], list)


async def test_get_certification_detail_without_auth(client: AsyncClient) -> None:
    """Verify that unauthenticated requests to get certification details are rejected."""

    cert_id = uuid4()
    response = await client.get(f"/api/v1/admin/certifications/{cert_id}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


async def test_get_certification_detail_with_valid_admin_token(
    client: AsyncClient, admin_user: User
) -> None:
    """Verify that authenticated admins can access certification details."""

    token = _create_admin_token(admin_user.id)
    # Use a known test certification ID from the seeded data
    cert_id = "aaaa1111-0000-0000-0000-000000000001"

    response = await client.get(
        f"/api/v1/admin/certifications/{cert_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should return 200 with certification details since we're using seeded data
    assert response.status_code == 200
    data = response.json()
    assert "certification" in data
    assert "kitchen_name" in data


async def test_verify_certification_without_auth(client: AsyncClient) -> None:
    """Verify that unauthenticated requests to verify certifications are rejected."""

    cert_id = uuid4()
    verification_request = {
        "action": "verify",
        "notes": "Looks good",
    }

    response = await client.post(
        f"/api/v1/admin/certifications/{cert_id}/verify",
        json=verification_request,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


async def test_verify_certification_with_valid_admin_token(
    client: AsyncClient, admin_user: User
) -> None:
    """Verify that authenticated admins can verify certifications."""

    token = _create_admin_token(admin_user.id)
    # Use a known pending certification from seeded data
    cert_id = "aaaa1111-0000-0000-0000-000000000001"

    verification_request = {
        "action": "verify",
        "notes": "All requirements met",
    }

    response = await client.post(
        f"/api/v1/admin/certifications/{cert_id}/verify",
        json=verification_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should successfully verify the certification
    assert response.status_code == 200
    data = response.json()
    assert "new_status" in data


async def test_verify_certification_with_regular_user_token(
    client: AsyncClient, regular_user: User
) -> None:
    """Verify that non-admin users cannot verify certifications."""

    token = _create_admin_token(regular_user.id)
    cert_id = uuid4()

    verification_request = {
        "action": "verify",
        "notes": "Attempting to verify",
    }

    response = await client.post(
        f"/api/v1/admin/certifications/{cert_id}/verify",
        json=verification_request,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin not authorized"
