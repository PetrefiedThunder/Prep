"""Connector for synchronising inventory data from MarketMan."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, MutableMapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

try:  # pragma: no cover - optional dependency at runtime
    import requests
except Exception:  # pragma: no cover - gracefully degrade if requests missing
    requests = None  # type: ignore

from sqlalchemy import select
from sqlalchemy.orm import Session

from prep.inventory.errors import ConnectorError
from prep.models.orm import InventoryItem, InventoryLot, Supplier

LOGGER = logging.getLogger("inventory.marketman")
if not LOGGER.handlers:
    LOGGER.addHandler(logging.NullHandler())


def _to_decimal(value: Any) -> Decimal:
    """Convert arbitrary numeric input to :class:`~decimal.Decimal`."""

    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError, TypeError):
        return Decimal("0")


def _parse_date(value: Any) -> datetime | None:
    """Parse an ISO-8601 string into a timezone-aware datetime."""

    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _extract_date(value: Any) -> datetime | None:
    """Coerce raw values to a UTC datetime when possible."""

    parsed = _parse_date(value)
    if parsed is None:
        return None
    return parsed.astimezone(UTC)


class MarketManConnector:
    """Simple REST client for MarketMan inventory endpoints."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: int = 15,
        session: requests.Session | None = None,
    ) -> None:
        if not requests:
            raise RuntimeError("requests is required to use MarketManConnector")

        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout = timeout
        self._session = session or requests.Session()

    # --------------------------
    # HTTP helpers
    # --------------------------
    def _request(self, method: str, path: str, **kwargs: Any) -> Mapping[str, Any]:
        url = f"{self.base_url}{path.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Authorization", f"Bearer {self.api_key}")
        response = self._session.request(
            method,
            url,
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )
        if response.status_code >= 400:
            raise ConnectorError(
                "MarketMan", f"{method} {path} failed", status_code=response.status_code
            )
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ConnectorError("MarketMan", "Invalid JSON response") from exc
        if isinstance(payload, Mapping):
            return payload
        raise ConnectorError("MarketMan", "Unexpected response payload shape")

    def _get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return self._request("GET", path, params=params)

    # --------------------------
    # Public API
    # --------------------------
    def fetch_inventory_items(self) -> list[Mapping[str, Any]]:
        """Return raw inventory items from MarketMan."""

        payload = self._get("inventory/items")
        items = payload.get("items") if isinstance(payload, Mapping) else None
        if isinstance(items, list):
            return items  # type: ignore[return-value]
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        return []

    def fetch_purchases(self) -> list[Mapping[str, Any]]:
        """Return purchase orders to map lot receipts."""

        payload = self._get("purchases")
        purchases = payload.get("purchases") if isinstance(payload, Mapping) else None
        if isinstance(purchases, list):
            return purchases  # type: ignore[return-value]
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        return []

    def fetch_suppliers(self) -> list[Mapping[str, Any]]:
        """Return supplier catalogue entries from MarketMan."""

        payload = self._get("suppliers")
        suppliers = payload.get("suppliers") if isinstance(payload, Mapping) else None
        if isinstance(suppliers, list):
            return suppliers  # type: ignore[return-value]
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        return []

    def sync_inventory(
        self,
        db_session: Session,
        *,
        kitchen_id: UUID,
        host_id: UUID,
    ) -> list[InventoryItem]:
        """Fetch data from MarketMan and upsert into Prep's inventory tables."""

        supplier_records = self.fetch_suppliers()
        supplier_lookup: MutableMapping[str, Supplier] = {}
        for record in supplier_records:
            external_id = str(record.get("id") or record.get("supplier_id") or "")
            if not external_id:
                continue
            supplier = db_session.execute(
                select(Supplier).where(
                    Supplier.external_id == external_id,
                    Supplier.source == "marketman",
                )
            ).scalar_one_or_none()
            if not supplier:
                supplier = Supplier(
                    external_id=external_id,
                    name=str(record.get("name") or record.get("company_name") or "Supplier"),
                    source="marketman",
                )
            supplier.contact_email = record.get("email") or record.get("contact_email")
            supplier.phone_number = record.get("phone") or record.get("phone_number")
            supplier.address = record.get("address")
            db_session.add(supplier)
            supplier_lookup[external_id] = supplier

        purchase_records = self.fetch_purchases()
        purchase_lookup: dict[str, Mapping[str, Any]] = {
            str(entry.get("id") or entry.get("purchase_id")): entry
            for entry in purchase_records
            if entry.get("id") or entry.get("purchase_id")
        }

        now = datetime.now(UTC)
        items: list[InventoryItem] = []
        for raw_item in self.fetch_inventory_items():
            external_id = str(raw_item.get("id") or raw_item.get("item_id") or "")
            if not external_id:
                LOGGER.debug("Skipping MarketMan item without identifier: %s", raw_item)
                continue

            stmt = select(InventoryItem).where(
                InventoryItem.external_id == external_id,
                InventoryItem.source == "marketman",
                InventoryItem.kitchen_id == kitchen_id,
            )
            item = db_session.execute(stmt).scalar_one_or_none()
            if not item:
                item = InventoryItem(
                    external_id=external_id,
                    source="marketman",
                    kitchen_id=kitchen_id,
                    host_id=host_id,
                    name=str(raw_item.get("name") or raw_item.get("item_name") or "Ingredient"),
                    unit=str(raw_item.get("unit") or raw_item.get("uom") or "ea"),
                )
            item.name = str(raw_item.get("name") or raw_item.get("item_name") or item.name)
            item.sku = raw_item.get("sku") or raw_item.get("item_code")
            item.category = raw_item.get("category") or raw_item.get("category_name")
            item.unit = str(raw_item.get("unit") or raw_item.get("uom") or item.unit)
            item.par_level = _to_decimal(raw_item.get("par_level") or raw_item.get("par"))
            supplier_reference = raw_item.get("supplier_id") or raw_item.get("vendor_id")
            if supplier_reference:
                item.supplier = supplier_lookup.get(str(supplier_reference))
            item.last_synced_at = now
            item.shared_shelf_available = bool(
                raw_item.get("shareable")
                or raw_item.get("shared_shelf")
                or raw_item.get("allow_sharing")
            )

            lots_payload = raw_item.get("lots") or raw_item.get("batches") or []
            if not isinstance(lots_payload, Iterable):
                lots_payload = []

            existing_lots = {lot.external_id: lot for lot in item.lots if lot.external_id}
            seen_lot_ids: set[str] = set()

            for raw_lot in lots_payload:
                if not isinstance(raw_lot, Mapping):
                    continue
                raw_lot_id = (
                    raw_lot.get("id")
                    or raw_lot.get("lot_id")
                    or raw_lot.get("batch_id")
                    or raw_lot.get("external_id")
                )
                lot_external_id = str(raw_lot_id) if raw_lot_id else None
                lot = None
                if lot_external_id and lot_external_id in existing_lots:
                    lot = existing_lots[lot_external_id]
                else:
                    lot = InventoryLot(item=item)
                lot.external_id = lot_external_id
                lot.quantity = _to_decimal(
                    raw_lot.get("quantity") or raw_lot.get("on_hand") or raw_lot.get("available")
                )
                lot.unit = str(raw_lot.get("unit") or raw_lot.get("uom") or item.unit)
                expiry_raw = raw_lot.get("expiry_date") or raw_lot.get("expiration_date")
                expiry_dt = _parse_date(expiry_raw)
                lot.expiry_date = expiry_dt.date() if expiry_dt else None

                purchase_id = raw_lot.get("purchase_id") or raw_lot.get("order_id")
                purchase = purchase_lookup.get(str(purchase_id)) if purchase_id else None
                received_source = raw_lot.get("received_at") or raw_lot.get("delivery_date")
                if purchase and not received_source:
                    received_source = (
                        purchase.get("received_at")
                        or purchase.get("delivery_date")
                        or purchase.get("created_at")
                    )
                lot.received_at = _extract_date(received_source)
                lot.source_reference = (
                    str(purchase_id)
                    if purchase_id
                    else str(raw_lot.get("reference") or raw_lot.get("po_number") or "")
                ) or None

                db_session.add(lot)
                if lot_external_id:
                    seen_lot_ids.add(lot_external_id)

            for external_lot_id, lot in list(existing_lots.items()):
                if external_lot_id and external_lot_id not in seen_lot_ids:
                    db_session.delete(lot)

            total_quantity = sum((lot.quantity for lot in item.lots), Decimal("0"))
            item.total_quantity = total_quantity
            expiries = [lot.expiry_date for lot in item.lots if lot.expiry_date]
            item.oldest_expiry = min(expiries) if expiries else None
            db_session.add(item)
            items.append(item)

        db_session.flush()
        return items
