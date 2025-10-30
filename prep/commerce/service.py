"""Omni-channel fulfillment orchestration."""

from __future__ import annotations

from datetime import datetime

from prep.commerce import models
from prep.commerce.production import ProductionScheduler
from prep.commerce.shopify import ShopifyConnector
from prep.commerce.tiktok import TikTokShopConnector
from prep.data_pipeline.cdc import CDCStreamManager
from prep.pos.oracle_simphony import FranchiseSyncService


class OmnichannelFulfillmentService:
    """Ingest orders, auto-schedule production, and push fulfillment updates."""

    def __init__(
        self,
        shopify: ShopifyConnector,
        tiktok: TikTokShopConnector,
        scheduler: ProductionScheduler,
        franchise_sync: FranchiseSyncService,
        cdc_stream: CDCStreamManager,
    ) -> None:
        self._shopify = shopify
        self._tiktok = tiktok
        self._scheduler = scheduler
        self._franchise_sync = franchise_sync
        self._cdc = cdc_stream

    async def ingest_orders(self, since: datetime | None = None) -> list[models.Order]:
        shopify_orders = await self._shopify.fetch_orders(since)
        tiktok_orders = await self._tiktok.fetch_orders(since)
        orders = shopify_orders + tiktok_orders
        await self._cdc.publish(
            "commerce.orders.ingested",
            {
                "shopify": len(shopify_orders),
                "tiktok": len(tiktok_orders),
                "total": len(orders),
            },
            {"shopify": "integer", "tiktok": "integer", "total": "integer"},
        )
        return orders

    async def schedule_and_fulfill(
        self, orders: list[models.Order]
    ) -> list[models.ProductionSlot]:
        slots = self._scheduler.schedule(orders)
        await self._franchise_sync.sync(orders)
        await self._push_fulfillment_updates(orders)
        await self._cdc.publish(
            "commerce.orders.scheduled",
            {
                "orders": [order.to_fulfillment_payload() for order in orders],
                "slot_count": len(slots),
            },
            {"orders": "array", "slot_count": "integer"},
        )
        return slots

    async def _push_fulfillment_updates(self, orders: list[models.Order]) -> None:
        for order in orders:
            await self._shopify.update_fulfillment(order)
            await self._tiktok.update_fulfillment(order)


__all__ = ["OmnichannelFulfillmentService"]
