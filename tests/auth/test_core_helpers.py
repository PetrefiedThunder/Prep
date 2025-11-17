"""Tests for core authentication helpers in prep.auth.core."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.auth.core import decode_and_validate_jwt, load_user_from_db
from prep.models.db import Base, User, UserRole

# Test secrets - only for testing!
TEST_SECRET = "test-secret-key-only-for-testing"
TEST_AUDIENCE = "test-audience"


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory async SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture()
async def active_admin_user(db_session: AsyncSession) -> User:
    """Create an active admin user in the database."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password="hashed_password",
        role=UserRole.ADMIN,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture()
async def inactive_user(db_session: AsyncSession) -> User:
    """Create an inactive user in the database."""
    user = User(
        id=uuid4(),
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password="hashed_password",
        role=UserRole.CUSTOMER,
        is_active=False,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture()
async def suspended_user(db_session: AsyncSession) -> User:
    """Create a suspended user in the database."""
    user = User(
        id=uuid4(),
        email="suspended@example.com",
        full_name="Suspended User",
        hashed_password="hashed_password",
        role=UserRole.HOST,
        is_active=True,
        is_suspended=True,
        suspension_reason="Terms violation",
        suspended_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture()
async def host_user(db_session: AsyncSession) -> User:
    """Create an active host user in the database."""
    user = User(
        id=uuid4(),
        email="host@example.com",
        full_name="Test Host",
        hashed_password="hashed_password",
        role=UserRole.HOST,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def create_test_jwt(
    user_id: str,
    secret: str = TEST_SECRET,
    audience: str | None = TEST_AUDIENCE,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a test JWT token."""
    payload = {
        "sub": user_id,
        "iat": datetime.now(UTC),
    }

    if audience:
        payload["aud"] = audience

    if expires_delta is not None:
        payload["exp"] = datetime.now(UTC) + expires_delta
    else:
        payload["exp"] = datetime.now(UTC) + timedelta(minutes=15)

    return jwt.encode(payload, secret, algorithm=algorithm)


# ============================================================================
# Tests for decode_and_validate_jwt
# ============================================================================


def test_decode_valid_jwt():
    """Test decoding a valid JWT returns the payload."""
    user_id = str(uuid4())
    token = create_test_jwt(user_id)

    payload = decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)

    assert payload["sub"] == user_id
    assert payload["aud"] == TEST_AUDIENCE
    assert "exp" in payload
    assert "iat" in payload


def test_decode_jwt_without_audience():
    """Test decoding a JWT without audience validation."""
    user_id = str(uuid4())
    token = create_test_jwt(user_id, audience=None)

    payload = decode_and_validate_jwt(token, TEST_SECRET, audience=None)

    assert payload["sub"] == user_id
    assert "aud" not in payload


def test_decode_jwt_with_custom_algorithm():
    """Test decoding a JWT with a non-default algorithm."""
    user_id = str(uuid4())
    token = create_test_jwt(user_id, algorithm="HS512")

    payload = decode_and_validate_jwt(token, TEST_SECRET, algorithms=["HS512"])

    assert payload["sub"] == user_id


def test_decode_expired_jwt():
    """Test that expired JWTs raise 401 with appropriate message."""
    user_id = str(uuid4())
    # Create token that expired 1 hour ago
    token = create_test_jwt(user_id, expires_delta=timedelta(hours=-1))

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_decode_jwt_wrong_audience():
    """Test that JWTs with wrong audience raise 401."""
    user_id = str(uuid4())
    token = create_test_jwt(user_id, audience="wrong-audience")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)

    assert exc_info.value.status_code == 401
    assert "audience" in exc_info.value.detail.lower()


def test_decode_jwt_wrong_signature():
    """Test that JWTs with invalid signature raise 401."""
    user_id = str(uuid4())
    token = create_test_jwt(user_id, secret="wrong-secret")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)

    assert exc_info.value.status_code == 401
    assert "signature" in exc_info.value.detail.lower()


def test_decode_malformed_jwt():
    """Test that malformed JWTs raise 401."""
    malformed_tokens = [
        "not.a.token",
        "too-short",
        "",
        "header.payload",  # Missing signature
        "a.b.c.d",  # Too many parts
    ]

    for token in malformed_tokens:
        with pytest.raises(HTTPException) as exc_info:
            decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)

        assert exc_info.value.status_code == 401


# ============================================================================
# Tests for load_user_from_db
# ============================================================================


@pytest.mark.anyio
async def test_load_active_user_success(db_session: AsyncSession, active_admin_user: User):
    """Test successfully loading an active user from the database."""
    user = await load_user_from_db(active_admin_user.id, db_session)

    assert user.id == active_admin_user.id
    assert user.email == active_admin_user.email
    assert user.is_active is True
    assert user.is_suspended is False


@pytest.mark.anyio
async def test_load_user_with_role_check_success(db_session: AsyncSession, active_admin_user: User):
    """Test loading a user with correct role succeeds."""
    user = await load_user_from_db(
        active_admin_user.id, db_session, require_role=UserRole.ADMIN
    )

    assert user.role == UserRole.ADMIN


@pytest.mark.anyio
async def test_load_user_with_role_mismatch(db_session: AsyncSession, host_user: User):
    """Test loading a user with wrong role raises 403."""
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(host_user.id, db_session, require_role=UserRole.ADMIN)

    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_load_inactive_user_fails(db_session: AsyncSession, inactive_user: User):
    """Test that inactive users cannot be loaded when require_active=True."""
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(inactive_user.id, db_session, require_active=True)

    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_load_suspended_user_fails(db_session: AsyncSession, suspended_user: User):
    """Test that suspended users cannot be loaded when require_active=True."""
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(suspended_user.id, db_session, require_active=True)

    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_load_inactive_user_allowed_when_not_required(
    db_session: AsyncSession, inactive_user: User
):
    """Test that inactive users can be loaded when require_active=False."""
    user = await load_user_from_db(inactive_user.id, db_session, require_active=False)

    assert user.id == inactive_user.id
    assert user.is_active is False


@pytest.mark.anyio
async def test_load_nonexistent_user(db_session: AsyncSession):
    """Test that loading a nonexistent user raises 403."""
    fake_user_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(fake_user_id, db_session)

    assert exc_info.value.status_code == 403
    assert "not authorized" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_load_user_no_enumeration(db_session: AsyncSession):
    """Test that error messages don't leak whether user exists (user enumeration)."""
    fake_user_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(fake_user_id, db_session)

    # Should be generic "not authorized", not "user not found"
    assert "user not found" not in exc_info.value.detail.lower()
    assert "not authorized" in exc_info.value.detail.lower()


# ============================================================================
# Integration test: JWT decode + DB load
# ============================================================================


@pytest.mark.anyio
async def test_full_auth_flow_success(db_session: AsyncSession, active_admin_user: User):
    """Test complete auth flow: decode JWT then load user from DB."""
    # Step 1: Create a valid JWT for the user
    token = create_test_jwt(str(active_admin_user.id))

    # Step 2: Decode and validate JWT
    payload = decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)
    assert payload["sub"] == str(active_admin_user.id)

    # Step 3: Load user from database
    from uuid import UUID

    user_id = UUID(payload["sub"])
    user = await load_user_from_db(
        user_id, db_session, require_active=True, require_role=UserRole.ADMIN
    )

    assert user.id == active_admin_user.id
    assert user.email == active_admin_user.email
    assert user.role == UserRole.ADMIN


@pytest.mark.anyio
async def test_full_auth_flow_deleted_user(db_session: AsyncSession):
    """Test that valid JWT for deleted user still fails (prevents zombie sessions)."""
    # Create user
    user = User(
        id=uuid4(),
        email="deleted@example.com",
        full_name="Soon Deleted",
        hashed_password="hashed",
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Create valid JWT
    token = create_test_jwt(str(user.id))

    # Delete user from database
    await db_session.delete(user)
    await db_session.flush()

    # JWT is still valid...
    payload = decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)
    assert payload["sub"] == str(user.id)

    # ...but DB lookup fails (CORRECT BEHAVIOR!)
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(user.id, db_session)

    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_full_auth_flow_suspended_after_jwt_issued(
    db_session: AsyncSession, host_user: User
):
    """Test that user suspended after JWT issuance cannot authenticate (real-time enforcement)."""
    # Create valid JWT while user is active
    token = create_test_jwt(str(host_user.id))

    # Suspend user
    host_user.is_suspended = True
    host_user.suspension_reason = "Terms violation"
    host_user.suspended_at = datetime.now(UTC)
    await db_session.flush()

    # JWT is still valid...
    payload = decode_and_validate_jwt(token, TEST_SECRET, audience=TEST_AUDIENCE)
    assert payload["sub"] == str(host_user.id)

    # ...but DB lookup fails due to suspension (CORRECT BEHAVIOR!)
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(host_user.id, db_session, require_active=True)

    assert exc_info.value.status_code == 403
