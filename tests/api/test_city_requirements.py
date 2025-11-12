from fastapi.testclient import TestClient

from api.city.requirements import get_policy_event_stream
from api.index import create_app

client = TestClient(create_app(include_full_router=False, include_legacy_mounts=False))


def _reset_events() -> None:
    stream = get_policy_event_stream()
    stream.bigquery.events.clear()
    stream.snowflake.events.clear()


def test_requirements_payload_includes_counts_and_rationales() -> None:
    _reset_events()
    response = client.get("/city/san francisco/requirements")
    assert response.status_code == 200
    payload = response.json()

    assert payload["jurisdiction"] == "san_francisco"
    assert payload["status"] in {"ready", "attention_required"}
    assert payload["validation"]["blocking_count"] >= 0

    counts = payload["validation"]["counts_by_party"]
    assert counts["kitchen_operator"] >= 1
    assert "change_candidates" in counts
    assert counts["change_candidates"] == len(payload["change_candidates"])

    rationales = payload["rationales"]
    assert "kitchen_operator" in rationales
    assert isinstance(rationales["kitchen_operator"], str) and rationales["kitchen_operator"]


def test_policy_decision_event_emitted_once_per_status() -> None:
    _reset_events()

    first = client.get("/city/oakland/requirements")
    assert first.status_code == 200

    second = client.get("/city/oakland/requirements")
    assert second.status_code == 200

    stream = get_policy_event_stream()
    events = stream.bigquery.events
    assert len(events) == 1
    event = events[0]
    assert event.name == "policy.decision"
    assert event.payload["jurisdiction"] == "oakland"
    assert event.payload["status"] == first.json()["status"]


def test_unknown_city_returns_404() -> None:
    response = client.get("/city/atlantis/requirements")
    assert response.status_code == 404
