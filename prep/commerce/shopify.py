"""Shopify Admin API integration layer."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from prep.commerce import models


class ShopifyClientError(RuntimeError):
    """Raised when the Shopify API returns an unexpected response."""


class ShopifyConnector:
    """Fetch orders and push fulfillment updates to Shopify."""

    def __init__(
        self,
        store_domain: str | None,
        api_token: str | None,
        api_version: str = "2024-01",
    ) -> None:
        self._store_domain = store_domain
        self._api_token = api_token
        self._api_version = api_version

    @property
    def is_configured(self) -> bool:
        return bool(self._store_domain and self._api_token)

    @property
    def base_url(self) -> str:
        if not self._store_domain:
            raise ShopifyClientError("Shopify store domain is not configured")
        return f"https://{self._store_domain}/admin/api/{self._api_version}"

    def _headers(self) -> dict[str, str]:
        if not self._api_token:
            raise ShopifyClientError("Shopify API token is missing")
        return {"X-Shopify-Access-Token": self._api_token}

    async def fetch_orders(self, since: datetime | None = None) -> list[models.Order]:
        if not self.is_configured:
            return []
        params = {"status": "open"}
        if since:
            params["created_at_min"] = since.isoformat()
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get("/orders.json", headers=self._headers(), params=params)
            response.raise_for_status()
            data = response.json()
        orders: Iterable[dict[str, Any]] = data.get("orders", [])
        normalized: list[models.Order] = []
        for item in orders:
            normalized.append(
                models.Order(
                    id=str(item["id"]),
                    source=models.OrderSource.SHOPIFY,
                    created_at=models.normalize_timestamp(item["created_at"]),
                    due_at=models.normalize_timestamp(
                        item.get("fulfillment_status_at") or item["created_at"]
                    ),
                    location_id=str(item.get("location_id") or "default"),
                    customer_name=item.get("customer", {}).get("first_name", "Guest"),
                    lines=models.coerce_order_lines(
                        line
                        for line in item.get("line_items", [])
                        if line.get("requires_shipping") is not False
                    ),
                )
            )
        return normalized

    async def update_fulfillment(self, order: models.Order) -> None:
        if not self.is_configured:
            return
        payload = {"fulfillment": {"status": order.status}}
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post(
                f"/orders/{order.id}/fulfillments.json",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()


__all__ = ["ShopifyConnector", "ShopifyClientError"]
