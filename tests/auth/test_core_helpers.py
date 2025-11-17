"""Unit tests for core authentication helpers in prep.auth.core."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.auth.core import decode_and_validate_jwt, load_user_from_db, verify_admin_roles
from prep.models.orm import Base, User, UserRole


# --- JWT Decoding Tests ---


def _b64_encode(data: bytes) -> str:
    """Helper to base64-encode data for JWT manipulation."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def test_decode_jwt_success():
    """Test successful JWT decode with valid token."""
    secret = "test-secret-key"
    payload = {"sub": "user-123", "roles": ["admin"], "exp": datetime.now(UTC) + timedelta(hours=1)}
    token = jwt.encode(payload, secret, algorithm="HS256")

    decoded = decode_and_validate_jwt(token, secret, audience=None, algorithms=["HS256"])

    assert decoded["sub"] == "user-123"
    assert decoded["roles"] == ["admin"]


def test_decode_jwt_with_audience():
    """Test JWT decode with audience validation."""
    secret = "test-secret"
    audience = "prep-api"
    payload = {
        "sub": "user-456",
        "aud": audience,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    decoded = decode_and_validate_jwt(token, secret, audience=audience, algorithms=["HS256"])

    assert decoded["sub"] == "user-456"
    assert decoded["aud"] == audience


def test_decode_jwt_invalid_signature():
    """Test JWT decode fails with wrong secret."""
    secret = "correct-secret"
    wrong_secret = "wrong-secret"
    payload = {"sub": "user", "exp": datetime.now(UTC) + timedelta(hours=1)}
    token = jwt.encode(payload, secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, wrong_secret, audience=None, algorithms=["HS256"])

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "signature" in exc_info.value.detail.lower()


def test_decode_jwt_expired_token():
    """Test JWT decode fails with expired token."""
    secret = "test-secret"
    payload = {"sub": "user", "exp": datetime.now(UTC) - timedelta(hours=1)}  # Expired 1 hour ago
    token = jwt.encode(payload, secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, secret, audience=None, algorithms=["HS256"])

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in exc_info.value.detail.lower()


def test_decode_jwt_wrong_audience():
    """Test JWT decode fails with wrong audience."""
    secret = "test-secret"
    payload = {
        "sub": "user",
        "aud": "wrong-audience",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, secret, audience="correct-audience", algorithms=["HS256"])

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "audience" in exc_info.value.detail.lower()


def test_decode_jwt_unsupported_algorithm():
    """Test JWT decode fails with disallowed algorithm."""
    secret = "test-secret"
    header = _b64_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8"))
    payload_data = _b64_encode(json.dumps({"sub": "user"}).encode("utf-8"))
    token = f"{header}.{payload_data}."

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, secret, audience=None, algorithms=["HS256", "RS256"])

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "algorithm" in exc_info.value.detail.lower()


def test_decode_jwt_invalid_token_format():
    """Test JWT decode fails with malformed token."""
    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt("not.a.valid.jwt", "secret", audience=None, algorithms=["HS256"])

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_jwt_no_secret():
    """Test JWT decode fails when secret is not configured."""
    token = "any.token.here"

    with pytest.raises(HTTPException) as exc_info:
        decode_and_validate_jwt(token, secret="", audience=None, algorithms=["HS256"])

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "secret not configured" in exc_info.value.detail.lower()


# --- Database User Loading Tests ---


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


@pytest.mark.anyio
async def test_load_user_active_user(db_session: AsyncSession):
    """Test loading an active user from database."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email="active@example.com",
        full_name="Active User",
        role=UserRole.CUSTOMER,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.commit()

    loaded = await load_user_from_db(user_id, db_session, require_active=True)

    assert loaded.id == user_id
    assert loaded.email == "active@example.com"
    assert loaded.is_active is True


@pytest.mark.anyio
async def test_load_user_inactive_rejected(db_session: AsyncSession):
    """Test loading inactive user raises 403."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email="inactive@example.com",
        full_name="Inactive User",
        role=UserRole.CUSTOMER,
        is_active=False,  # Inactive
        is_suspended=False,
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(user_id, db_session, require_active=True)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "inactive" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_load_user_suspended_rejected(db_session: AsyncSession):
    """Test loading suspended user raises 403."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email="suspended@example.com",
        full_name="Suspended User",
        role=UserRole.HOST,
        is_active=True,
        is_suspended=True,  # Suspended
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(user_id, db_session, require_active=True)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "inactive" in exc_info.value.detail.lower() or "suspended" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_load_user_not_found(db_session: AsyncSession):
    """Test loading non-existent user raises 403."""
    non_existent_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(non_existent_id, db_session, require_active=True)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_load_user_require_active_false(db_session: AsyncSession):
    """Test loading inactive user succeeds when require_active=False."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email="any@example.com",
        full_name="Any User",
        role=UserRole.CUSTOMER,
        is_active=False,
        is_suspended=True,
    )
    db_session.add(user)
    await db_session.commit()

    # Should succeed even though user is inactive and suspended
    loaded = await load_user_from_db(user_id, db_session, require_active=False)

    assert loaded.id == user_id
    assert loaded.is_active is False
    assert loaded.is_suspended is True


@pytest.mark.anyio
async def test_load_user_require_role(db_session: AsyncSession):
    """Test loading user with specific role requirement."""
    admin_id = uuid4()
    admin = User(
        id=admin_id,
        email="admin@example.com",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_suspended=False,
    )
    db_session.add(admin)
    await db_session.commit()

    # Should succeed
    loaded = await load_user_from_db(admin_id, db_session, require_role=UserRole.ADMIN)
    assert loaded.role == UserRole.ADMIN

    # Should fail with wrong role
    with pytest.raises(HTTPException) as exc_info:
        await load_user_from_db(admin_id, db_session, require_role=UserRole.CUSTOMER)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "role" in exc_info.value.detail.lower()


# --- Admin Role Verification Tests ---


def test_verify_admin_roles_admin():
    """Test admin role verification succeeds for ADMIN."""
    roles = {"admin", "customer"}
    verify_admin_roles(roles)  # Should not raise


def test_verify_admin_roles_operator_admin():
    """Test admin role verification succeeds for OPERATOR_ADMIN."""
    roles = {"operator_admin"}
    verify_admin_roles(roles)  # Should not raise


def test_verify_admin_roles_support_analyst():
    """Test admin role verification succeeds for SUPPORT_ANALYST."""
    roles = {"support_analyst", "host"}
    verify_admin_roles(roles)  # Should not raise


def test_verify_admin_roles_regulatory_admin():
    """Test admin role verification succeeds for REGULATORY_ADMIN."""
    roles = {"regulatory_admin"}
    verify_admin_roles(roles)  # Should not raise


def test_verify_admin_roles_no_admin_role():
    """Test admin role verification fails for non-admin roles."""
    roles = {"customer", "host"}

    with pytest.raises(HTTPException) as exc_info:
        verify_admin_roles(roles)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "admin role required" in exc_info.value.detail.lower()


def test_verify_admin_roles_empty():
    """Test admin role verification fails for empty role set."""
    roles = set()

    with pytest.raises(HTTPException) as exc_info:
        verify_admin_roles(roles)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
