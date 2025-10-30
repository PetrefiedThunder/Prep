"""Tests for SMT verification stub."""
from __future__ import annotations

from apps.policy_engine.verify import verify_rules_smt


def test_verify_rules_returns_ok() -> None:
    result = verify_rules_smt(b"package policies")
    assert result["ok"] is True
