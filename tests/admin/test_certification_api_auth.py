"""Tests for certification API authentication and authorization.

NOTE: These tests are blocked by existing ORM relationship issues in the codebase.
Once the BusinessPermit/BusinessProfile relationship is fixed, implement these tests.

Test Coverage Required:
- GET /api/v1/admin/certifications/pending
- GET /api/v1/admin/certifications/{cert_id}
- POST /api/v1/admin/certifications/{cert_id}/verify
"""

from __future__ import annotations

import pytest

# TODO: Implement these tests once ORM issues are resolved
# from collections.abc import AsyncGenerator
# from uuid import uuid4
# from fastapi import FastAPI
# from httpx import AsyncClient
# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
# from prep.admin.certification_api import certification_router
# from prep.admin.dependencies import get_current_admin
# from prep.models.admin import AdminUser
# from prep.models.db import Base, User, UserRole


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_get_pending_certifications_no_auth():
    """Test that GET /pending without auth returns 401."""
    # TODO: Implement test that verifies 401 when no Authorization header
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_get_pending_certifications_invalid_token():
    """Test that GET /pending with invalid JWT returns 401."""
    # TODO: Implement test with malformed/expired/wrong-signature token
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_get_pending_certifications_non_admin():
    """Test that GET /pending with non-admin user returns 403."""
    # TODO: Implement test with valid JWT but role=HOST or role=CUSTOMER
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_get_pending_certifications_success():
    """Test that GET /pending with valid admin token returns 200."""
    # TODO: Implement test with valid admin JWT
    # Should return PendingCertificationsResponse with correct structure
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_get_certification_detail_no_auth():
    """Test that GET /{cert_id} without auth returns 401."""
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_get_certification_detail_success():
    """Test that GET /{cert_id} with valid admin token returns certification details."""
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_verify_certification_no_auth():
    """Test that POST /{cert_id}/verify without auth returns 401."""
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_verify_certification_non_admin():
    """Test that POST /{cert_id}/verify with non-admin returns 403."""
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_verify_certification_success():
    """Test that POST /{cert_id}/verify with valid admin executes verification."""
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_deleted_admin_cannot_authenticate():
    """Test that admin deleted from DB cannot use valid JWT (prevents zombie sessions)."""
    # TODO: Critical security test!
    # 1. Create admin user
    # 2. Generate valid JWT
    # 3. Delete admin from DB
    # 4. Verify JWT decode succeeds but DB lookup fails with 403
    pass


@pytest.mark.skip(reason="Blocked by ORM BusinessPermit/BusinessProfile relationship issue")
@pytest.mark.anyio
async def test_suspended_admin_cannot_authenticate():
    """Test that suspended admin cannot use valid JWT (real-time enforcement)."""
    # TODO: Critical security test!
    # 1. Create active admin
    # 2. Generate valid JWT
    # 3. Suspend admin (is_suspended=True)
    # 4. Verify JWT decode succeeds but DB lookup fails with 403
    pass
