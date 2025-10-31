from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from prep.models import PolicyDecision
from prep.regulatory.policy_logging import _hash_input, write_policy_decision


def test_hash_input_is_deterministic() -> None:
    payload_a = {"city": "San Francisco", "state": "CA", "nested": {"value": 1}}
    payload_b = {"state": "CA", "nested": {"value": 1}, "city": "San Francisco"}

    assert _hash_input(payload_a) == _hash_input(payload_b)


@pytest.mark.usefixtures("db_session")
def test_write_policy_decision_creates_record(db_session: Session) -> None:
    payload = {"city": "San Francisco", "state": "CA"}
    result = {"decision": "allow", "evaluated_at": datetime.utcnow().isoformat()}

    record = write_policy_decision(
        region="CA",
        jurisdiction="San Francisco",
        package_path="prep/policy",
        decision="allow",
        rationale="All checks passed" * 80,  # ensures trimming
        error="".join(["none"] * 300),
        input_payload=payload,
        result_payload=result,
        duration_ns=52_000_000,
        session=db_session,
        triggered_by="pytest",
        trace_id="trace-123",
        request_id="facility-456",
    )

    db_session.flush()
    persisted = db_session.query(PolicyDecision).filter(PolicyDecision.id == record.id).one()

    assert persisted.duration_ms == 52
    assert persisted.request_hash == _hash_input(payload)
    assert len(persisted.rationale or "") <= 1024
    assert len(persisted.error or "") <= 1024
    assert persisted.triggered_by == "pytest"
    assert persisted.trace_id == "trace-123"
    assert persisted.request_id == "facility-456"
