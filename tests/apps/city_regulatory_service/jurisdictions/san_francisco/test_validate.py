from datetime import date
from typing import Any

import pytest

from apps.city_regulatory_service.jurisdictions.san_francisco import validate


class DummyResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def test_validate_permit_serializes_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], timeout: float) -> DummyResponse:
        recorded["url"] = url
        recorded["json"] = json
        recorded["timeout"] = timeout
        return DummyResponse({"result": "allow"})

    monkeypatch.setattr(validate.requests, "post", fake_post)

    permit = {
        "permit": {
            "id": "sf-food-123",
            "expiry": date(2024, 12, 31),
        }
    }

    result = validate.validate_permit(permit, opa_url="https://opa.example/v1/data")

    assert recorded["json"] == {
        "input": {
            "permit": {
                "id": "sf-food-123",
                "expiry": "2024-12-31",
            }
        }
    }
    assert result == {"result": "allow"}
