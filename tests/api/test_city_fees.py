from __future__ import annotations

from fastapi.testclient import TestClient

from api.index import create_app

client = TestClient(create_app(include_full_router=False, include_legacy_mounts=False))


def _assert_ok(city: str) -> None:
    response = client.get(f"/city/{city}/fees")
    assert response.status_code == 200
    body = response.json()
    assert body.get("jurisdiction")
    assert isinstance(body.get("paperwork"), list)
    assert isinstance(body.get("fees"), list) and body["fees"]
    totals = body.get("totals", {})
    assert totals.get("one_time_cents", -1) >= 0
    assert totals.get("recurring_annualized_cents", -1) >= 0
    validation = body.get("validation", {})
    assert isinstance(validation.get("is_valid"), bool)


def test_sf_fees() -> None:
    _assert_ok("sf")


def test_oakland_fees() -> None:
    _assert_ok("oakland")


def test_berkeley_fees() -> None:
    _assert_ok("berkeley")


def test_sanjose_fees() -> None:
    _assert_ok("san jose")


def test_paloalto_fees() -> None:
    _assert_ok("palo alto")


def test_joshua_tree_fees() -> None:
    _assert_ok("joshua tree")


def test_unsupported_city() -> None:
    response = client.get("/city/atlantis/fees")
    assert response.status_code == 404
