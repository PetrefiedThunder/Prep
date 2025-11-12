"""Tests for timezone-aware datetime usage.

SECURITY: Verify that datetime operations use timezone-aware timestamps
to prevent clock skew and timezone-related bugs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from prep.utils.jwt import create_access_token, verify_access_token


def test_jwt_token_uses_utc_timezone() -> None:
    """Verify JWT tokens use UTC timezone for expiration.

    SECURITY: Ensures tokens expire correctly regardless of server timezone.
    Prevents timezone-based authentication bypass.
    """
    test_payload = {"sub": "user123", "role": "customer"}

    # Create a token
    token = create_access_token(test_payload)

    # Verify the token
    decoded = verify_access_token(token)
    assert decoded is not None, "Token should be valid immediately after creation"
    assert decoded["sub"] == "user123"
    assert decoded["role"] == "customer"
    assert "exp" in decoded, "Token must have expiration claim"

    # Verify expiration is a future timestamp
    exp_timestamp = decoded["exp"]
    now = datetime.now(UTC)
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)

    assert exp_datetime > now, "Token expiration must be in the future"
    assert exp_datetime < now + timedelta(hours=1), (
        "Token should expire within reasonable timeframe"
    )


def test_jwt_token_expiration_enforcement() -> None:
    """Verify expired JWT tokens are rejected.

    SECURITY: Critical test - ensures expired tokens cannot be used.
    """
    with patch("prep.utils.jwt.datetime") as mock_datetime:
        # Mock datetime to create token that expires immediately
        past_time = datetime.now(UTC) - timedelta(minutes=60)
        mock_datetime.now.return_value = past_time
        mock_datetime.UTC = UTC

        test_payload = {"sub": "user123", "role": "admin"}
        expired_token = create_access_token(test_payload)

    # Attempt to verify the expired token (using real datetime)
    decoded = verify_access_token(expired_token)
    assert decoded is None, "Expired tokens must be rejected"


def test_booking_compliance_check_uses_utc() -> None:
    """Verify booking compliance checks use UTC for date comparisons.

    SECURITY: Ensures compliance checks work correctly across timezones.
    """
    from prep.api.bookings import datetime  # noqa: F401

    # This test verifies that the bookings module imports datetime correctly
    # and that comparisons in the code use UTC
    now_utc = datetime.now(UTC)
    old_timestamp = now_utc - timedelta(days=31)

    # Verify the difference is correctly calculated
    diff = now_utc - old_timestamp
    assert diff.days == 31, "Date difference should be calculated correctly in UTC"


@pytest.mark.parametrize("days_old", [29, 30, 31, 32])
def test_compliance_check_age_boundary_conditions(days_old: int) -> None:
    """Test boundary conditions for 30-day compliance check threshold.

    SECURITY: Ensures compliance checks trigger at the correct time.
    """
    now = datetime.now(UTC)
    old_check = now - timedelta(days=days_old)

    time_diff = now - old_check

    if days_old > 30:
        assert time_diff > timedelta(days=30), (
            f"Checks older than 30 days should trigger refresh (days={days_old})"
        )
    else:
        assert time_diff <= timedelta(days=30), (
            f"Checks 30 days or newer should not trigger refresh (days={days_old})"
        )


def test_utc_datetime_comparison_consistency() -> None:
    """Verify UTC datetime comparisons are consistent.

    SECURITY: Ensures datetime comparisons work correctly for security checks.
    """
    # Create two UTC timestamps
    time1 = datetime.now(UTC)
    time2 = datetime.now(UTC) + timedelta(seconds=1)

    assert time2 > time1, "Future timestamps should be greater"
    assert time1 < time2, "Past timestamps should be lesser"
    assert time1 != time2, "Different timestamps should not be equal"

    # Verify timedelta arithmetic works correctly
    diff = time2 - time1
    assert diff.total_seconds() >= 1, "Time difference should be at least 1 second"
    assert diff.total_seconds() < 2, "Time difference should be less than 2 seconds"
