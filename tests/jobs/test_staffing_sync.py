from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest import mock

import pytest

import importlib.util
import pathlib
import sys
import types

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _Session:
        def request(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - stub
            raise NotImplementedError("requests is not installed in the test environment")

    def _request(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover - stub
        raise NotImplementedError("requests is not installed in the test environment")

    requests_stub.Session = _Session
    requests_stub.request = _request
    sys.modules["requests"] = requests_stub

if "Prep" not in sys.modules:
    prep_module = types.ModuleType("Prep")
    docusign_module = types.ModuleType("Prep.docusign_client")

    class _DocuSignError(Exception):
        pass

    class _DocuSignClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - stub
            raise NotImplementedError("DocuSign client is not available in tests")

    docusign_module.DocuSignClient = _DocuSignClient
    docusign_module.DocuSignError = _DocuSignError
    sys.modules["Prep"] = prep_module
    sys.modules["Prep.docusign_client"] = docusign_module

if "prep.models.db" not in sys.modules:
    prep_models_module = types.ModuleType("prep.models.db")
    prep_models_module.SessionLocal = None
    prep_models_module.init_db = None
    sys.modules.setdefault("prep.models", types.ModuleType("prep.models"))
    sys.modules["prep.models.db"] = prep_models_module

from apps.scheduling.staff_alignment import BookingWindow, reconcile_staff_availability
from integrations.staffing.deputy import DeputyClient
from integrations.staffing.seven_shifts import SevenShiftsClient
from modules.staff.models import StaffShift

_STAFFING_SYNC_PATH = pathlib.Path(__file__).resolve().parents[2] / "jobs" / "staffing_sync.py"
_SPEC = importlib.util.spec_from_file_location("jobs.staffing_sync", _STAFFING_SYNC_PATH)
assert _SPEC and _SPEC.loader  # pragma: no cover - import guard
_STAFFING_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("jobs", types.ModuleType("jobs"))
sys.modules[_SPEC.name] = _STAFFING_MODULE
_SPEC.loader.exec_module(_STAFFING_MODULE)

run_staffing_sync = _STAFFING_MODULE.run_staffing_sync


class _FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> Dict[str, Any]:
        return self._payload


@pytest.fixture()
def utc_now() -> datetime:
    return datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_seven_shifts_client_refreshes_token_and_paginates(utc_now: datetime) -> None:
    session = mock.Mock()
    auth_calls: List[Dict[str, Any]] = []
    get_attempt = {"count": 0}

    def side_effect(method: str, url: str, **kwargs: Any) -> _FakeResponse:
        if method.lower() == "post":
            auth_calls.append(kwargs["json"])
            token_index = len(auth_calls)
            return _FakeResponse(200, {"access_token": f"token-{token_index}", "expires_in": 60})

        get_attempt["count"] += 1
        attempt = get_attempt["count"]
        headers = kwargs["headers"]
        if attempt == 1:
            assert headers["Authorization"] == "Bearer token-1"
            return _FakeResponse(401, {"message": "expired"})
        if attempt == 2:
            assert headers["Authorization"] == "Bearer token-2"
            params = kwargs["params"]
            assert "cursor" not in params
            payload = {
                "data": [
                    {
                        "id": "shift-1",
                        "user": {"id": "1", "name": "Taylor"},
                        "start": "2024-01-01T09:00:00Z",
                        "end": "2024-01-01T12:00:00Z",
                        "role": "prep",
                    }
                ],
                "pagination": {"next_cursor": "cursor-2"},
            }
            return _FakeResponse(200, payload)
        if attempt == 3:
            params = kwargs["params"]
            assert params["cursor"] == "cursor-2"
            return _FakeResponse(
                200,
                {
                    "data": [
                        {
                            "id": "shift-2",
                            "user": {"id": "2", "name": "Jordan"},
                            "start": "2024-01-01T12:00:00Z",
                            "end": "2024-01-01T15:00:00Z",
                            "role": "line",
                        }
                    ]
                },
            )
        raise AssertionError("Unexpected request order")

    session.request.side_effect = side_effect

    client = SevenShiftsClient(
        client_id="abc",
        client_secret="def",
        base_url="https://example.com",
        session=session,
    )

    schedules = list(
        client.iter_schedules(
            start=utc_now,
            end=utc_now + timedelta(hours=8),
            per_page=1,
        )
    )

    assert len(schedules) == 2
    assert session.request.call_count == 5  # 2 auth, 3 data fetches
    assert auth_calls[0]["grant_type"] == "client_credentials"


def test_deputy_client_paginates_results(utc_now: datetime) -> None:
    session = mock.Mock()
    call_order: List[str] = []

    def side_effect(method: str, url: str, **kwargs: Any) -> _FakeResponse:
        call_order.append(method.lower())
        if method.lower() == "post":
            return _FakeResponse(200, {"access_token": "token", "expires_in": 60})

        params = kwargs["params"]
        if params["offset"] == 0:
            assert params["page_size"] == 2
            payload = {
                "results": [
                    {
                        "Id": "r1",
                        "Employee": {"Id": "a", "DisplayName": "Sam"},
                        "StartTime": "2024-01-01T10:00:00Z",
                        "EndTime": "2024-01-01T11:00:00Z",
                    }
                ],
                "meta": {"next_offset": 2},
            }
            return _FakeResponse(200, payload)
        assert params["offset"] == 2
        return _FakeResponse(
            200,
            {
                "results": [
                    {
                        "Id": "r2",
                        "Employee": {"Id": "b", "DisplayName": "Riley"},
                        "StartTime": "2024-01-01T11:00:00Z",
                        "EndTime": "2024-01-01T12:30:00Z",
                    }
                ]
            },
        )

    session.request.side_effect = side_effect

    client = DeputyClient(
        client_id="abc",
        client_secret="def",
        refresh_token="ghi",
        base_url="https://example.com",
        session=session,
    )

    shifts = list(
        client.iter_shifts(
            start=utc_now,
            end=utc_now + timedelta(hours=5),
            page_size=2,
        )
    )

    assert len(shifts) == 2
    assert call_order.count("post") == 1
    assert call_order.count("get") == 2


def test_reconcile_staff_availability_matches_roles(utc_now: datetime) -> None:
    shift = StaffShift(
        id="s1",
        external_id="s1",
        staff_id="staff-1",
        source="seven_shifts",
        start=utc_now,
        end=utc_now + timedelta(hours=4),
        roles=("prep", "line"),
        location_id="kitchen-1",
    )
    bookings = [
        BookingWindow(
            id="b1",
            start=utc_now + timedelta(minutes=30),
            end=utc_now + timedelta(hours=1, minutes=30),
            required_roles=("prep",),
            location_id="kitchen-1",
        ),
        BookingWindow(
            id="b2",
            start=utc_now + timedelta(hours=2),
            end=utc_now + timedelta(hours=3),
            required_roles=("line",),
            location_id="kitchen-1",
        ),
        BookingWindow(
            id="b3",
            start=utc_now + timedelta(hours=3),
            end=utc_now + timedelta(hours=4, minutes=30),
            required_roles=("bar",),
            location_id="kitchen-1",
        ),
    ]

    result = reconcile_staff_availability([shift], bookings)

    assert len(result.assignments) == 1
    assert {booking.id for booking in result.assignments[0].bookings} == {"b1", "b2"}
    assert [booking.id for booking in result.unfilled_bookings] == ["b3"]


def test_run_staffing_sync_returns_snapshot(utc_now: datetime) -> None:
    class StubSeven:
        def fetch_schedules(self, *, start: datetime, end: datetime, **_: Any) -> List[Dict[str, Any]]:
            return [
                {
                    "id": "seven-1",
                    "user": {"id": "1", "name": "Taylor", "roles": ["prep"]},
                    "start": "2024-01-01T09:00:00Z",
                    "end": "2024-01-01T12:00:00Z",
                    "location_id": "kitchen-1",
                    "role": "prep",
                }
            ]

    class StubDeputy:
        def fetch_shifts(self, *, start: datetime, end: datetime, **_: Any) -> List[Dict[str, Any]]:
            return [
                {
                    "Id": "dep-1",
                    "Employee": {"Id": "99", "DisplayName": "Riley", "roles": ["line"]},
                    "StartTime": "2024-01-01T12:00:00Z",
                    "EndTime": "2024-01-01T15:00:00Z",
                    "OperationalUnit": {"Id": "kitchen-1"},
                    "role": "line",
                }
            ]

    bookings = [
        BookingWindow(
            id="booking-1",
            start=utc_now + timedelta(hours=1),
            end=utc_now + timedelta(hours=2),
            required_roles=("prep",),
            location_id="kitchen-1",
        ),
        BookingWindow(
            id="booking-2",
            start=utc_now + timedelta(hours=3),
            end=utc_now + timedelta(hours=4),
            required_roles=("line",),
            location_id="kitchen-1",
        ),
    ]

    result = run_staffing_sync(
        seven_shifts=StubSeven(),
        deputy=StubDeputy(),
        bookings=bookings,
        start=utc_now,
        end=utc_now + timedelta(hours=6),
    )

    assert result.total_staff() == 2
    assert result.total_shifts() == 2
    assert len(result.alignment.assignments) == 2
    assert {booking.id for booking in result.alignment.assignments[0].bookings} == {"booking-1"}
    assert {booking.id for booking in result.alignment.assignments[1].bookings} == {"booking-2"}
