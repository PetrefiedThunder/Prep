"""Tests for admin authentication dependencies in prep.admin.dependencies."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.admin.dependencies import get_current_admin
from prep.models.admin import AdminUser
from prep.models.orm import Base, User, UserRole


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def _create_admin_jwt(user_id: str, permissions: list[str] | None = None) -> str:
    """Helper to create a valid admin JWT token."""
    secret = os.getenv("ADMIN_JWT_SECRET", "test-admin-secret")
    audience = os.getenv("ADMIN_JWT_AUDIENCE", "prep-admin")

    payload = {
        "sub": user_id,
        "permissions": permissions or ["admin:full"],
        "aud": audience,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }

    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.anyio
async def test_get_current_admin_success(db_session: AsyncSession):
    """Test successful admin authentication with valid token and active admin user."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create active admin user in database
    admin_id = uuid4()
    admin = User(
        id=admin_id,
        email="admin@example.com",
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(admin)
    await db_session.commit()

    # Create valid JWT token
    token = _create_admin_jwt(str(admin_id), permissions=["admin:full", "users:manage"])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Call get_current_admin
    result = await get_current_admin(credentials=credentials, db=db_session)

    # Verify AdminUser is returned with correct data
    assert isinstance(result, AdminUser)
    assert result.id == admin_id
    assert result.email == "admin@example.com"
    assert result.full_name == "Test Admin"
    assert result.permissions == ["admin:full", "users:manage"]


@pytest.mark.anyio
async def test_get_current_admin_no_credentials(db_session: AsyncSession):
    """Test admin auth fails when no credentials provided."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=None, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "not authenticated" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_get_current_admin_invalid_token(db_session: AsyncSession):
    """Test admin auth fails with invalid JWT token."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.anyio
async def test_get_current_admin_expired_token(db_session: AsyncSession):
    """Test admin auth fails with expired token."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    admin_id = uuid4()

    # Create expired token (expired 1 hour ago)
    payload = {
        "sub": str(admin_id),
        "permissions": ["admin:full"],
        "aud": "prep-admin",
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    token = jwt.encode(payload, "test-admin-secret", algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_get_current_admin_wrong_audience(db_session: AsyncSession):
    """Test admin auth fails with wrong token audience."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    admin_id = uuid4()

    # Create token with wrong audience
    payload = {
        "sub": str(admin_id),
        "permissions": ["admin:full"],
        "aud": "wrong-audience",  # Wrong!
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "test-admin-secret", algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "audience" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_get_current_admin_missing_subject(db_session: AsyncSession):
    """Test admin auth fails when token has no 'sub' claim."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create token without 'sub' claim
    payload = {
        "permissions": ["admin:full"],
        "aud": "prep-admin",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "test-admin-secret", algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "payload" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_get_current_admin_invalid_subject_format(db_session: AsyncSession):
    """Test admin auth fails when 'sub' is not a valid UUID."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create token with non-UUID subject
    payload = {
        "sub": "not-a-uuid",
        "permissions": ["admin:full"],
        "aud": "prep-admin",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "test-admin-secret", algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "subject" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_get_current_admin_user_not_found(db_session: AsyncSession):
    """Test admin auth fails when user doesn't exist in database."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create token for non-existent user
    non_existent_id = uuid4()
    token = _create_admin_jwt(str(non_existent_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_get_current_admin_inactive_user(db_session: AsyncSession):
    """Test admin auth fails when user is inactive."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create inactive admin user
    admin_id = uuid4()
    admin = User(
        id=admin_id,
        email="inactive@example.com",
        full_name="Inactive Admin",
        role=UserRole.ADMIN,
        is_active=False,  # Inactive!
        is_suspended=False,
    )
    db_session.add(admin)
    await db_session.commit()

    token = _create_admin_jwt(str(admin_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_get_current_admin_suspended_user(db_session: AsyncSession):
    """Test admin auth fails when user is suspended."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create suspended admin user
    admin_id = uuid4()
    admin = User(
        id=admin_id,
        email="suspended@example.com",
        full_name="Suspended Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_suspended=True,  # Suspended!
    )
    db_session.add(admin)
    await db_session.commit()

    token = _create_admin_jwt(str(admin_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_get_current_admin_non_admin_role(db_session: AsyncSession):
    """Test admin auth fails when user has non-admin role."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    # Create user with CUSTOMER role (not admin)
    user_id = uuid4()
    user = User(
        id=user_id,
        email="customer@example.com",
        full_name="Customer User",
        role=UserRole.CUSTOMER,  # Not an admin!
        is_active=True,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.commit()

    token = _create_admin_jwt(str(user_id))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=credentials, db=db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "role" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_get_current_admin_permissions_handling(db_session: AsyncSession):
    """Test permissions are correctly extracted from JWT payload."""
    os.environ["ADMIN_JWT_SECRET"] = "test-admin-secret"
    os.environ["ADMIN_JWT_AUDIENCE"] = "prep-admin"

    admin_id = uuid4()
    admin = User(
        id=admin_id,
        email="admin@example.com",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(admin)
    await db_session.commit()

    # Test with list of permissions
    token = _create_admin_jwt(str(admin_id), permissions=["read:all", "write:kitchens"])
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    result = await get_current_admin(credentials=credentials, db=db_session)
    assert result.permissions == ["read:all", "write:kitchens"]

    # Test with no permissions in token
    payload = {
        "sub": str(admin_id),
        "aud": "prep-admin",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token_no_perms = jwt.encode(payload, "test-admin-secret", algorithm="HS256")
    credentials_no_perms = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_no_perms)
    result_no_perms = await get_current_admin(credentials=credentials_no_perms, db=db_session)
    assert result_no_perms.permissions == []

    # Test with non-list permissions (should default to empty list)
    payload_bad = {
        "sub": str(admin_id),
        "permissions": "not-a-list",
        "aud": "prep-admin",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token_bad = jwt.encode(payload_bad, "test-admin-secret", algorithm="HS256")
    credentials_bad = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_bad)
    result_bad = await get_current_admin(credentials=credentials_bad, db=db_session)
    assert result_bad.permissions == []
