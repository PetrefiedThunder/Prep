from datetime import datetime, timezone
from decimal import Decimal

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
if not hasattr(sqlalchemy, "select"):
    pytest.skip("sqlalchemy is not available", allow_module_level=True)

from prep.pos.toast import ToastWebhookProcessor


def test_normalize_order_extracts_fields() -> None:
    processor = ToastWebhookProcessor()
    payload = {
        "orderGuid": "order-1",
        "status": "CLOSED",
        "orderNumber": "42",
        "guestCount": 3,
        "openedDate": "2024-01-01T10:00:00Z",
        "closedDate": "2024-01-01T12:15:00Z",
        "check": {
            "totals": {
                "grandTotal": {"amount": "4599"},
                "currencyCode": "USD",
            }
        },
    }

    event = processor.normalize_order(payload)

    assert event.external_id == "order-1"
    assert event.status == "closed"
    assert event.order_number == "42"
    assert event.total_amount == Decimal("45.99")
    assert event.currency == "USD"
    assert event.guest_count == 3
    assert event.opened_at == datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert event.closed_at == datetime(2024, 1, 1, 12, 15, tzinfo=timezone.utc)
