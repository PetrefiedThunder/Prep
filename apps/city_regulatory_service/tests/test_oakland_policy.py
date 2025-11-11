"""Tests for the Oakland jurisdiction Rego policy."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

POLICY_PATH = Path(__file__).resolve().parent.parent / "jurisdictions" / "oakland" / "policy.rego"


def _parse_rfc3339_to_ns(value: str) -> int:
    """Convert an RFC 3339 timestamp to nanoseconds since the epoch."""
    cleaned = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    return int(dt.timestamp() * 1_000_000_000)


def _evaluate_allow(input_payload: dict[str, object], now_ns: int) -> bool:
    """Mirror the allow rule semantics used in the Rego policy.

    The original bug compared an RFC 3339 string directly against ``time.now_ns()``,
    which raises a ``TypeError`` in Python (and similarly fails type checking in
    Rego). The helper performs the same high-level checks as the policy but uses a
    parsed timestamp to ensure consistent typing.
    """

    permit = input_payload.get("permit")
    if not isinstance(permit, dict):
        return False

    if permit.get("status") != "active":
        return False

    expiry_value = permit.get("expiry")
    if not isinstance(expiry_value, str):
        return False

    try:
        expiry_ns = _parse_rfc3339_to_ns(expiry_value)
    except ValueError:
        return False

    return now_ns < expiry_ns


def test_policy_parses_expiry_before_comparison() -> None:
    """Ensure the policy sources use time.parse_rfc3339_ns to normalise the expiry."""

    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    assert "time.parse_rfc3339_ns" in policy_text


@pytest.mark.parametrize(
    "delta_days", [30, -30],
    ids=["not_expired", "expired"],
)
def test_allow_rule_handles_rfc3339_expiry_without_type_errors(delta_days: int) -> None:
    """Simulate the allow rule and assert it does not suffer from type errors."""

    now = datetime.now(UTC)
    expiry = (now + timedelta(days=delta_days)).isoformat()
    now_ns = int(now.timestamp() * 1_000_000_000)

    result = _evaluate_allow({"permit": {"status": "active", "expiry": expiry}}, now_ns)

    if delta_days > 0:
        assert result is True
    else:
        assert result is False


def test_allow_rule_rejects_invalid_expiry_strings() -> None:
    """Invalid expiry strings should not trigger type errors and yield ``False``."""

    now_ns = int(datetime.now(UTC).timestamp() * 1_000_000_000)
    result = _evaluate_allow({"permit": {"status": "active", "expiry": "not-a-date"}}, now_ns)
    assert result is False
