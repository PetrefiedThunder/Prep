from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from prep.commerce import models
from prep.commerce.production import ProductionScheduler
from prep.commerce.service import OmnichannelFulfillmentService
from prep.commerce.shopify import ShopifyConnector
from prep.commerce.tiktok import TikTokShopConnector
from prep.data_pipeline.cdc import build_cdc_stream
from prep.pos.oracle_simphony import FranchiseSyncService, OracleSimphonyClient
from prep.settings import Settings


@pytest.mark.asyncio
async def test_omnichannel_service_schedules_and_syncs(monkeypatch) -> None:
    shopify_order = models.Order(
        id="shopify-1",
        source=models.OrderSource.SHOPIFY,
        created_at=datetime(2024, 1, 1, 10, tzinfo=timezone.utc),
        due_at=datetime(2024, 1, 1, 12, tzinfo=timezone.utc),
        location_id="location-a",
        customer_name="Alice",
        lines=[models.OrderLine(sku="SKU-1", quantity=5)],
    )
    tiktok_order = models.Order(
        id="tiktok-1",
        source=models.OrderSource.TIKTOK,
        created_at=datetime(2024, 1, 1, 11, tzinfo=timezone.utc),
        due_at=datetime(2024, 1, 1, 13, tzinfo=timezone.utc),
        location_id="location-b",
        customer_name="Bob",
        lines=[models.OrderLine(sku="SKU-2", quantity=3)],
    )

    shopify = ShopifyConnector(store_domain=None, api_token=None)
    tiktok = TikTokShopConnector(app_key=None, app_secret=None, access_token=None)
    monkeypatch.setattr(shopify, "fetch_orders", AsyncMock(return_value=[shopify_order]))
    monkeypatch.setattr(tiktok, "fetch_orders", AsyncMock(return_value=[tiktok_order]))
    shopify_update = AsyncMock()
    tiktok_update = AsyncMock()
    monkeypatch.setattr(shopify, "update_fulfillment", shopify_update)
    monkeypatch.setattr(tiktok, "update_fulfillment", tiktok_update)

    oracle_client = OracleSimphonyClient(
        host=None, username=None, password=None, enterprise_id=None
    )
    franchise_sync = FranchiseSyncService(oracle_client)
    sync_calls: list[tuple[str, int]] = []

    async def capture_sync(location_id: str, orders):
        sync_calls.append((location_id, len(list(orders))))

    monkeypatch.setattr(oracle_client, "sync_orders", AsyncMock(side_effect=capture_sync))

    scheduler = ProductionScheduler(slot_duration_minutes=60, max_capacity=20)
    cdc = build_cdc_stream(Settings())
    service = OmnichannelFulfillmentService(
        shopify=shopify,
        tiktok=tiktok,
        scheduler=scheduler,
        franchise_sync=franchise_sync,
        cdc_stream=cdc,
    )

    orders = await service.ingest_orders()
    assert len(orders) == 2

    slots = await service.schedule_and_fulfill(orders)

    assert all(order.status == "scheduled" for order in orders)
    assert sync_calls == [("location-a", 1), ("location-b", 1)]
    shopify_update.assert_awaited()
    tiktok_update.assert_awaited()
    assert len(slots) == 2
    assert not cdc.bigquery.events
    assert not cdc.snowflake.events
