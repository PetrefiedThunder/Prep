"""Toast POS webhook helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from .models import OrderEvent

_DEFAULT_BASE_URL = "https://toast-api.io"
_WEBHOOK_PATH = "/webhooks/v1/subscriptions"
_DEFAULT_EVENTS = ("ORDER_STATE_CHANGED",)


class ToastAPIError(RuntimeError):
    """Raised when the Toast API encounters an error."""


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_amount(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, dict):
        for key in ("decimalValue", "amount", "value"):
            if value.get(key) is not None:
                value = value[key]
                break
        else:
            return Decimal("0")
    amount = Decimal(str(value))
    if amount == 0:
        return Decimal("0")
    if amount == amount.to_integral_value() and amount >= 100:
        return amount / Decimal("100")
    return amount


def _extract_amount(payload: dict[str, Any]) -> tuple[Decimal, str]:
    check = payload.get("check") or {}
    totals = check.get("totals") or {}
    amount = totals.get("grandTotal")
    currency = (
        totals.get("currencyCode") or totals.get("currency") or payload.get("currency") or "USD"
    )
    if amount is None:
        amount = payload.get("totalAmount") or payload.get("grandTotal")
    return _normalize_amount(amount), currency


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ToastWebhookProcessor:
    """Utility class for Toast webhook subscriptions and normalization."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self._base_url, timeout=30.0)
            self._owns_client = True
        return self._client

    def subscribe_to_order_webhooks(
        self,
        *,
        callback_url: str,
        events: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise ToastAPIError("Toast API key is not configured")
        payload = {
            "callbackUrl": callback_url,
            "eventTypes": list(events or _DEFAULT_EVENTS),
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        response = self._get_client().post(_WEBHOOK_PATH, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ToastAPIError(
                f"Toast webhook subscription failed with status {response.status_code}: {response.text}"
            )
        return response.json()

    def normalize_order(self, payload: dict[str, Any]) -> OrderEvent:
        order_id = (
            payload.get("orderGuid")
            or payload.get("orderId")
            or payload.get("id")
            or payload.get("guid")
        )
        if not order_id:
            raise ToastAPIError("Toast webhook payload missing order identifier")
        status = (
            payload.get("status") or payload.get("orderStatus") or payload.get("state") or "open"
        )
        amount, currency = _extract_amount(payload)
        return OrderEvent(
            provider="toast",
            external_id=str(order_id),
            status=str(status).lower(),
            total_amount=amount,
            currency=currency,
            order_number=_coerce_str(
                payload.get("orderNumber")
                or payload.get("checkNumber")
                or payload.get("displayNumber")
            ),
            opened_at=_parse_datetime(
                payload.get("openedDate") or payload.get("openedAt") or payload.get("startTime")
            ),
            closed_at=_parse_datetime(
                payload.get("closedDate") or payload.get("closedAt") or payload.get("endTime")
            ),
            guest_count=_coerce_int(
                payload.get("guestCount") or payload.get("guests") or payload.get("partySize")
            ),
            raw=payload,
        )


__all__ = ["ToastWebhookProcessor", "ToastAPIError"]
