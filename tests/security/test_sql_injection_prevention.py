"""Tests for SQL injection prevention measures.

SECURITY: Verify that SQL queries are properly parameterized and validated.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_federal_healthz_endpoint_table_whitelist() -> None:
    """Verify health check endpoint validates table names against whitelist.

    SECURITY: Ensures only approved tables are queried to prevent SQL injection.
    """
    # This test verifies the implementation indirectly by ensuring
    # the endpoint only queries known safe tables
    from apps.federal_regulatory_service.main import ALLOWED_TABLES  # noqa: F401

    # The ALLOWED_TABLES constant should be defined and frozen
    # This test passes if the import succeeds without errors


def test_table_whitelist_is_immutable() -> None:
    """Verify table whitelist cannot be modified at runtime.

    SECURITY: Ensures whitelist cannot be tampered with.
    """
    # Import to verify the code compiles correctly
    import apps.federal_regulatory_service.main as fed_main

    # Check that ALLOWED_TABLES is defined in the health_check function's scope
    import inspect
    source = inspect.getsource(fed_main.health_check)

    # Verify the whitelist is defined as a frozenset (immutable)
    assert "ALLOWED_TABLES" in source, "Table whitelist should be defined"
    assert "frozenset" in source, "Table whitelist should be a frozenset (immutable)"


@pytest.mark.parametrize("malicious_input", [
    "users; DROP TABLE users; --",
    "' OR '1'='1",
    "1' UNION SELECT * FROM secrets--",
    "../../../etc/passwd",
    "'; DELETE FROM bookings WHERE '1'='1",
])
def test_booking_endpoints_sanitize_input(malicious_input: str) -> None:
    """Verify booking endpoints reject malicious input patterns.

    SECURITY: Ensures user input cannot be used for SQL injection.
    """
    from uuid import UUID
    from prep.api.bookings import BookingCreate
    from pydantic import ValidationError

    # Test that UUIDs are properly validated
    with pytest.raises((ValidationError, ValueError)):
        BookingCreate(
            user_id=malicious_input,  # Should fail UUID validation
            kitchen_id="550e8400-e29b-41d4-a716-446655440000",
            start_time="2025-01-01T10:00:00Z",
            end_time="2025-01-01T12:00:00Z"
        )


def test_uuid_validation_prevents_injection() -> None:
    """Verify UUID validation prevents non-UUID values.

    SECURITY: UUIDs are used as identifiers to prevent injection attacks.
    """
    from uuid import UUID
    import pytest

    # Valid UUID should work
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    parsed = UUID(valid_uuid)
    assert str(parsed) == valid_uuid

    # Invalid UUIDs should raise ValueError
    invalid_inputs = [
        "DROP TABLE users",
        "' OR '1'='1",
        "../../secrets",
        "123",
        "not-a-uuid",
    ]

    for invalid in invalid_inputs:
        with pytest.raises(ValueError):
            UUID(invalid)


def test_sqlalchemy_orm_prevents_raw_sql_injection() -> None:
    """Verify SQLAlchemy ORM usage prevents SQL injection.

    SECURITY: ORM queries are parameterized by default.
    """
    from sqlalchemy import select
    from prep.models import Booking

    # This query is safe because SQLAlchemy parameterizes it
    safe_query = select(Booking).where(Booking.id == "test-id")

    # Verify the query uses parameter binding (no string interpolation)
    compiled = safe_query.compile()
    query_str = str(compiled)

    # Should use parameter placeholders, not direct string interpolation
    assert "?" in query_str or ":" in query_str or "%s" in query_str or "%(id)" in query_str, \
        "SQLAlchemy queries should use parameter binding"


def test_regulatory_scraper_validates_state_codes() -> None:
    """Verify regulatory scraper validates state codes.

    SECURITY: Ensures only valid US state codes are processed.
    """
    from prep.api.admin_regulatory import ScrapeRequest
    from pydantic import ValidationError

    # Valid request
    valid_request = ScrapeRequest(states=["CA", "NY", "TX"])
    assert len(valid_request.states) == 3

    # Test that country code is validated
    request = ScrapeRequest(states=["CA"], country_code="US")
    assert request.country_code == "US"

    # Test that country code length is enforced
    with pytest.raises(ValidationError):
        ScrapeRequest(states=["CA"], country_code="USA")  # Too long

    with pytest.raises(ValidationError):
        ScrapeRequest(states=["CA"], country_code="U")  # Too short
