"""Composable workflows for omni-channel commerce integrations."""

from __future__ import annotations

from datetime import datetime

from prep.commerce import models
from prep.commerce.production import ProductionScheduler
from prep.commerce.service import OmnichannelFulfillmentService
from prep.commerce.shopify import ShopifyConnector
from prep.commerce.tiktok import TikTokShopConnector
from prep.data_pipeline.cdc import build_cdc_stream
from prep.pos.oracle_simphony import FranchiseSyncService, OracleSimphonyClient
from prep.settings import Settings


async def run_omnichannel_cycle(
    settings: Settings, since: datetime | None = None
) -> list[models.ProductionSlot]:
    """Fetch omni-channel orders, schedule production, and push fulfillment."""

    cdc_stream = build_cdc_stream(settings)
    shopify = ShopifyConnector(
        store_domain=settings.shopify_store_domain,
        api_token=settings.shopify_admin_api_token,
        api_version=settings.shopify_api_version,
    )
    tiktok = TikTokShopConnector(
        app_key=settings.tiktok_shop_app_key,
        app_secret=settings.tiktok_shop_app_secret,
        access_token=settings.tiktok_shop_access_token,
    )
    oracle_client = OracleSimphonyClient(
        host=str(settings.oracle_simphony_host) if settings.oracle_simphony_host else None,
        username=settings.oracle_simphony_username,
        password=settings.oracle_simphony_password,
        enterprise_id=settings.oracle_simphony_enterprise_id,
    )
    franchise_sync = FranchiseSyncService(oracle_client)
    scheduler = ProductionScheduler()
    service = OmnichannelFulfillmentService(
        shopify=shopify,
        tiktok=tiktok,
        scheduler=scheduler,
        franchise_sync=franchise_sync,
        cdc_stream=cdc_stream,
    )
    orders = await service.ingest_orders(since)
    if not orders:
        return []
    return await service.schedule_and_fulfill(orders)


__all__ = ["run_omnichannel_cycle"]
