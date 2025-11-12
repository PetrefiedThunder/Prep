"""Square POS connector implementation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from prep.models.orm import POSIntegration, POSTransaction

from .models import NormalizedTransaction
from .repository import POSIntegrationRepository

_SQUARE_API_VERSION = "2023-09-20"
_DEFAULT_BASE_URL = "https://connect.squareup.com"
_OAUTH_PATH = "/oauth2/token"
_LOCATIONS_PATH = "/v2/locations"
_TRANSACTIONS_PATH = "/v2/locations/{location_id}/transactions"


class SquareAPIError(RuntimeError):
    """Raised when the Square API returns an error."""


class SquarePOSOAuthToken:
    """OAuth token response from Square."""

    def __init__(
        self,
        *,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
        token_type: str = "bearer",
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.token_type = token_type


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise SquareAPIError(f"Invalid timestamp received from Square: {value}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _extract_amount(transaction: dict[str, Any]) -> tuple[Decimal, str]:
    tenders = transaction.get("tenders") or []
    total = Decimal("0")
    currency = "USD"
    for tender in tenders:
        money = tender.get("amount_money") or {}
        amount = money.get("amount")
        currency = money.get("currency") or currency
        if amount is None:
            continue
        total += Decimal(str(amount))
    if tenders:
        return (total / Decimal("100")) if total else Decimal("0"), currency
    money = (
        transaction.get("tenders", [{}])[0].get("amount_money")
        if tenders
        else transaction.get("amount_money")
    )
    if not money:
        return Decimal("0"), currency
    amount = Decimal(str(money.get("amount", 0)))
    currency = money.get("currency") or currency
    return amount / Decimal("100"), currency


def _resolve_status(transaction: dict[str, Any]) -> str:
    if "status" in transaction and transaction["status"]:
        return str(transaction["status"]).lower()
    tenders = transaction.get("tenders") or []
    for tender in tenders:
        card_details = tender.get("card_details") or {}
        if card_details.get("status"):
            return str(card_details["status"]).lower()
        if tender.get("type"):
            return str(tender["type"]).lower()
    return "completed"


class SquarePOSConnector:
    """Client for interacting with Square's POS APIs."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        http_client: httpx.AsyncClient | None = None,
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Square-Version": _SQUARE_API_VERSION},
            timeout=httpx.Timeout(30.0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def refresh_access_token(self, refresh_token: str) -> SquarePOSOAuthToken:
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        response = await self._client.post(_OAUTH_PATH, json=payload)
        if response.status_code >= 400:
            raise SquareAPIError(
                f"Square token refresh failed with status {response.status_code}: {response.text}"
            )
        data = response.json()
        return SquarePOSOAuthToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_at=_parse_timestamp(data.get("expires_at")),
            token_type=data.get("token_type", "bearer"),
        )

    async def _authorized_get(
        self, path: str, *, access_token: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self._client.get(path, headers=headers, params=params)
        if response.status_code >= 400:
            raise SquareAPIError(
                f"Square API request failed with status {response.status_code}: {response.text}"
            )
        return response.json()

    async def fetch_locations(self, access_token: str) -> list[dict[str, Any]]:
        payload = await self._authorized_get(_LOCATIONS_PATH, access_token=access_token)
        locations = payload.get("locations") or []
        return [
            location for location in locations if location.get("status", "ACTIVE") != "INACTIVE"
        ]

    async def fetch_transactions(
        self,
        *,
        access_token: str,
        location_id: str,
        begin_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if begin_time:
            params["begin_time"] = begin_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if end_time:
            params["end_time"] = end_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        payload = await self._authorized_get(
            _TRANSACTIONS_PATH.format(location_id=location_id),
            access_token=access_token,
            params=params or None,
        )
        return payload.get("transactions") or []

    def normalize_transaction(self, transaction: dict[str, Any]) -> NormalizedTransaction:
        amount, currency = _extract_amount(transaction)
        occurred_at = _parse_timestamp(transaction.get("created_at"))
        if occurred_at is None:
            raise SquareAPIError("Square transaction missing created_at timestamp")
        return NormalizedTransaction(
            provider="square",
            external_id=str(transaction.get("id")),
            amount=amount,
            currency=currency,
            status=_resolve_status(transaction),
            occurred_at=occurred_at,
            location_id=transaction.get("location_id"),
            raw=transaction,
        )

    async def sync_integration(
        self,
        *,
        repository: POSIntegrationRepository,
        integration: POSIntegration,
        lookback: timedelta | None = None,
    ) -> list[POSTransaction]:
        if not integration.refresh_token:
            raise SquareAPIError("Square integration is missing a refresh token")
        token = await self.refresh_access_token(integration.refresh_token)
        await repository.update_tokens(
            integration,
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            expires_at=token.expires_at,
        )
        now = datetime.now(UTC)
        begin_time = now - lookback if lookback else None
        transactions: list[POSTransaction] = []
        locations = await self.fetch_locations(token.access_token)
        for location in locations:
            location_id = location.get("id")
            if not location_id:
                continue
            raw_transactions = await self.fetch_transactions(
                access_token=token.access_token,
                location_id=str(location_id),
                begin_time=begin_time,
                end_time=now,
            )
            for raw in raw_transactions:
                normalized = self.normalize_transaction(raw)
                saved = await repository.upsert_transaction(integration, normalized)
                transactions.append(saved)
        await repository.touch_integrations([integration])
        return transactions


__all__ = ["SquarePOSConnector", "SquarePOSOAuthToken", "SquareAPIError"]
