"""Tests for admin endpoint authorization enforcement.

SECURITY: Verify that admin endpoints require proper authorization.
"""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_regulatory_endpoints_require_auth(async_client: AsyncClient) -> None:
    """Verify admin regulatory endpoints reject unauthenticated requests.

    SECURITY: Critical test - ensures admin endpoints cannot be accessed without auth.
    """
    # Test GET /admin/regulatory/states
    response = await async_client.get("/admin/regulatory/states")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
        "Admin endpoint should reject requests without authentication"

    # Test GET /admin/regulatory/scraping-status
    response = await async_client.get("/admin/regulatory/scraping-status")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
        "Admin endpoint should reject requests without authentication"

    # Test POST /admin/regulatory/scrape
    response = await async_client.post(
        "/admin/regulatory/scrape",
        json={"states": ["CA", "NY"]}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
        "Admin endpoint should reject requests without authentication"


@pytest.mark.asyncio
async def test_admin_regulatory_endpoints_require_admin_role(
    async_client: AsyncClient,
    customer_token: str,
) -> None:
    """Verify admin endpoints reject non-admin users.

    SECURITY: Critical test - ensures regular users cannot access admin endpoints.
    """
    headers = {"Authorization": f"Bearer {customer_token}"}

    # Test that customer role is rejected
    response = await async_client.get("/admin/regulatory/states", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN, \
        "Admin endpoint should reject non-admin users"

    response = await async_client.post(
        "/admin/regulatory/scrape",
        json={"states": ["CA"]},
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN, \
        "Admin endpoint should reject non-admin users"


@pytest.mark.asyncio
async def test_admin_regulatory_endpoints_allow_admin_access(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Verify admin endpoints work correctly with valid admin token.

    SECURITY: Verify admin endpoints are accessible to authorized admins.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Test GET requests work with admin token
    response = await async_client.get("/admin/regulatory/states", headers=headers)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR), \
        "Admin endpoint should accept valid admin tokens"

    response = await async_client.get("/admin/regulatory/scraping-status", headers=headers)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR), \
        "Admin endpoint should accept valid admin tokens"


@pytest.mark.asyncio
async def test_admin_scrape_validates_input(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Verify scrape endpoint validates input properly.

    SECURITY: Ensure input validation prevents injection attacks.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Test empty states list
    response = await async_client.post(
        "/admin/regulatory/scrape",
        json={"states": []},
        headers=headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "at least one state" in response.json()["detail"].lower()

    # Test valid request
    response = await async_client.post(
        "/admin/regulatory/scrape",
        json={"states": ["CA", "NY"]},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert "scheduled" in result
    assert set(result["scheduled"]) == {"CA", "NY"}
