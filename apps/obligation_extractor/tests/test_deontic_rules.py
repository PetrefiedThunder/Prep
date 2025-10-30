"""Tests for deontic consistency checks."""
from __future__ import annotations

from apps.obligation_extractor.validate import assert_deontic_consistency


def test_conflicting_obligation_and_prohibition_rejected() -> None:
    obligations = [
        {"subject": "host_kitchen", "action": "maintain_license", "type": "obligation"},
        {"subject": "host_kitchen", "action": "maintain_license", "type": "prohibition"},
    ]
    accepted, rejected = assert_deontic_consistency(obligations)
    assert len(accepted) == 1
    assert rejected[0]["reason"] == "conflicting deontic modal"
