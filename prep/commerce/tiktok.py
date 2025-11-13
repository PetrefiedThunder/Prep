"""TikTok Shop integration for order ingestion and fulfillment sync."""

from __future__ import annotations

from datetime import datetime

import httpx

from prep.commerce import models


class TikTokShopError(RuntimeError):
    """Raised for non-success responses from the TikTok Shop API."""


class TikTokShopConnector:
    """Bidirectional connector for the TikTok Shop order APIs."""

    def __init__(
        self,
        app_key: str | None,
        app_secret: str | None,
        access_token: str | None,
        base_url: str = "https://open-api.tiktokglobalshop.com",
    ) -> None:
        self._app_key = app_key
        self._app_secret = app_secret
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self._app_key and self._app_secret and self._access_token)

    async def fetch_orders(self, since: datetime | None = None) -> list[models.Order]:
        if not self.is_configured:
            return []
        params = {"access_token": self._access_token, "app_key": self._app_key}
        if since:
            params["create_time_from"] = int(since.timestamp())
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            response = await client.get("/api/orders/search", params=params)
            response.raise_for_status()
            data = response.json()
        orders = data.get("data", {}).get("orders", [])
        normalized: list[models.Order] = []
        for item in orders:
            normalized.append(
                models.Order(
                    id=str(item["order_id"]),
                    source=models.OrderSource.TIKTOK,
                    created_at=models.normalize_timestamp(item["create_time"]),
                    due_at=models.normalize_timestamp(
                        item.get("promise_delivery_time") or item["create_time"]
                    ),
                    location_id=str(item.get("warehouse_id") or "default"),
                    customer_name=item.get("recipient", {}).get("name", "Guest"),
                    lines=models.coerce_order_lines(item.get("line_items", [])),
                )
            )
        return normalized

    async def update_fulfillment(self, order: models.Order) -> None:
        if not self.is_configured:
            return
        payload = {
            "access_token": self._access_token,
            "app_key": self._app_key,
            "order_id": order.id,
            "status": order.status,
            "items": [{"sku": line.sku, "quantity": line.quantity} for line in order.lines],
        }
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            response = await client.post("/api/fulfillment/update", json=payload)
            response.raise_for_status()


__all__ = ["TikTokShopConnector", "TikTokShopError"]
