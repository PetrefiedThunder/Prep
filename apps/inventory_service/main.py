"""Inventory microservice exposing CRUD endpoints and transfer workflow."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Generator, List
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from prep.models.db import SessionLocal
from prep.models.orm import (
    InventoryItem,
    InventoryLot,
    InventoryTransfer,
    InventoryTransferStatus,
    Supplier,
)

app = FastAPI(title="Prep Inventory Service", version="1.0.0")


def _get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


DECIMAL_ZERO = Decimal("0")


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid quantity value")


def _recalculate_item(item: InventoryItem) -> None:
    item.total_quantity = sum((lot.quantity for lot in item.lots), DECIMAL_ZERO)
    expiries = [lot.expiry_date for lot in item.lots if lot.expiry_date]
    item.oldest_expiry = min(expiries) if expiries else None


def _apply_fifo_depletion(session: Session, item: InventoryItem, quantity: Decimal) -> date | None:
    remaining = quantity
    consumed_expiry: date | None = None
    sorted_lots = sorted(
        item.lots,
        key=lambda lot: (
            lot.expiry_date if lot.expiry_date is not None else date.max,
            lot.received_at if lot.received_at is not None else datetime.min,
        ),
    )
    for lot in sorted_lots:
        if remaining <= DECIMAL_ZERO:
            break
        available = lot.quantity
        if available <= remaining:
            remaining -= available
            if lot.expiry_date:
                consumed_expiry = (
                    lot.expiry_date
                    if consumed_expiry is None
                    else min(consumed_expiry, lot.expiry_date)
                )
            session.delete(lot)
        else:
            lot.quantity = available - remaining
            if lot.expiry_date and consumed_expiry is None:
                consumed_expiry = lot.expiry_date
            remaining = DECIMAL_ZERO
    if remaining > DECIMAL_ZERO:
        raise HTTPException(
            status_code=400,
            detail="Insufficient quantity available for FIFO depletion",
        )
    _recalculate_item(item)
    return consumed_expiry


def _create_lot_from_payload(item: InventoryItem, payload: "InventoryLotCreate") -> InventoryLot:
    lot = InventoryLot(
        item=item,
        quantity=_to_decimal(payload.quantity),
        unit=payload.unit or item.unit,
    )
    lot.expiry_date = payload.expiry_date
    lot.received_at = payload.received_at
    lot.source_reference = payload.source_reference
    return lot


class SupplierSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contact_email: str | None = None
    phone_number: str | None = None


class InventoryLotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quantity: Decimal
    unit: str
    expiry_date: date | None = None
    received_at: datetime | None = None
    source_reference: str | None = None


class InventoryTransferSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    to_kitchen_id: UUID
    approval_status: InventoryTransferStatus
    quantity: Decimal
    unit: str
    expiry_date: date | None = None


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kitchen_id: UUID
    host_id: UUID
    name: str
    sku: str | None = None
    category: str | None = None
    unit: str
    total_quantity: Decimal
    par_level: Decimal | None = None
    oldest_expiry: date | None = None
    shared_shelf_available: bool
    supplier: SupplierSummary | None = None
    lots: List[InventoryLotRead] = Field(default_factory=list)
    pending_transfers: List[InventoryTransferSummary] = Field(default_factory=list)


class InventoryLotCreate(BaseModel):
    quantity: Decimal
    unit: str
    expiry_date: date | None = None
    received_at: datetime | None = None
    source_reference: str | None = None


class InventoryItemCreate(BaseModel):
    kitchen_id: UUID
    host_id: UUID
    name: str
    unit: str
    sku: str | None = None
    category: str | None = None
    par_level: Decimal | None = None
    supplier_id: UUID | None = None
    shared_shelf_available: bool = False
    lots: List[InventoryLotCreate] = Field(default_factory=list)


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    sku: str | None = None
    category: str | None = None
    par_level: Decimal | None = None
    shared_shelf_available: bool | None = None
    supplier_id: UUID | None = None
    lots: List[InventoryLotCreate] | None = None


class InventoryAdjustmentRequest(BaseModel):
    quantity_delta: Decimal
    expiry_date: date | None = None
    received_at: datetime | None = None
    unit: str | None = None
    source_reference: str | None = None


class InventoryTransferRequest(BaseModel):
    item_id: UUID
    from_kitchen_id: UUID
    to_kitchen_id: UUID
    requested_by_host_id: UUID
    quantity: Decimal
    unit: str
    expiry_date: date | None = None
    notes: str | None = None


class InventoryTransferUpdateRequest(BaseModel):
    approval_status: InventoryTransferStatus
    approved_by_host_id: UUID | None = None
    notes: str | None = None


class InventoryTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    from_kitchen_id: UUID
    to_kitchen_id: UUID
    requested_by_host_id: UUID
    approved_by_host_id: UUID | None = None
    approval_status: InventoryTransferStatus
    quantity: Decimal
    unit: str
    requested_at: datetime
    approved_at: datetime | None = None
    expiry_date: date | None = None
    notes: str | None = None


def _serialize_item(item: InventoryItem) -> InventoryItemResponse:
    pending_transfers = [
        transfer
        for transfer in item.transfers
        if transfer.approval_status == InventoryTransferStatus.PENDING
    ]
    return InventoryItemResponse(
        id=item.id,
        kitchen_id=item.kitchen_id,
        host_id=item.host_id,
        name=item.name,
        sku=item.sku,
        category=item.category,
        unit=item.unit,
        total_quantity=item.total_quantity,
        par_level=item.par_level,
        oldest_expiry=item.oldest_expiry,
        shared_shelf_available=item.shared_shelf_available or bool(pending_transfers),
        supplier=item.supplier,
        lots=item.lots,
        pending_transfers=pending_transfers,
    )


@app.get("/healthz", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items", response_model=List[InventoryItemResponse])
async def list_inventory_items(
    kitchen_id: UUID | None = Query(default=None),
    session: Session = Depends(_get_session),
) -> List[InventoryItemResponse]:
    stmt = (
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.lots),
            joinedload(InventoryItem.supplier),
            joinedload(InventoryItem.transfers),
        )
        .order_by(InventoryItem.name)
    )
    if kitchen_id:
        stmt = stmt.where(InventoryItem.kitchen_id == kitchen_id)
    items = session.scalars(stmt).unique().all()
    return [_serialize_item(item) for item in items]


@app.post("/items", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    payload: InventoryItemCreate,
    session: Session = Depends(_get_session),
) -> InventoryItemResponse:
    supplier: Supplier | None = None
    if payload.supplier_id:
        supplier = session.get(Supplier, payload.supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    item = InventoryItem(
        kitchen_id=payload.kitchen_id,
        host_id=payload.host_id,
        name=payload.name,
        unit=payload.unit,
        sku=payload.sku,
        category=payload.category,
        par_level=payload.par_level,
        shared_shelf_available=payload.shared_shelf_available,
    )
    if supplier:
        item.supplier = supplier

    session.add(item)
    session.flush()

    for lot_payload in payload.lots:
        lot = _create_lot_from_payload(item, lot_payload)
        session.add(lot)

    _recalculate_item(item)
    session.add(item)
    session.commit()
    session.refresh(item)
    return _serialize_item(item)


@app.get("/items/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    item_id: UUID,
    session: Session = Depends(_get_session),
) -> InventoryItemResponse:
    item = session.execute(
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .options(
            joinedload(InventoryItem.lots),
            joinedload(InventoryItem.supplier),
            joinedload(InventoryItem.transfers),
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return _serialize_item(item)


@app.put("/items/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    session: Session = Depends(_get_session),
) -> InventoryItemResponse:
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if payload.name is not None:
        item.name = payload.name
    if payload.unit is not None:
        item.unit = payload.unit
    if payload.sku is not None:
        item.sku = payload.sku
    if payload.category is not None:
        item.category = payload.category
    if payload.par_level is not None:
        item.par_level = payload.par_level
    if payload.shared_shelf_available is not None:
        item.shared_shelf_available = payload.shared_shelf_available
    if payload.supplier_id is not None:
        supplier = session.get(Supplier, payload.supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        item.supplier = supplier

    if payload.lots is not None:
        for lot in list(item.lots):
            session.delete(lot)
        session.flush()
        for lot_payload in payload.lots:
            session.add(_create_lot_from_payload(item, lot_payload))

    _recalculate_item(item)
    session.add(item)
    session.commit()
    session.refresh(item)
    return _serialize_item(item)


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: UUID,
    session: Session = Depends(_get_session),
) -> None:
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    session.delete(item)
    session.commit()


@app.post("/items/{item_id}/adjust", response_model=InventoryItemResponse)
async def adjust_inventory_item(
    item_id: UUID,
    payload: InventoryAdjustmentRequest,
    session: Session = Depends(_get_session),
) -> InventoryItemResponse:
    item = session.execute(
        select(InventoryItem)
        .where(InventoryItem.id == item_id)
        .options(
            joinedload(InventoryItem.lots),
            joinedload(InventoryItem.transfers),
            joinedload(InventoryItem.supplier),
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    quantity_delta = _to_decimal(payload.quantity_delta)
    if quantity_delta == DECIMAL_ZERO:
        return _serialize_item(item)

    if quantity_delta < DECIMAL_ZERO:
        _apply_fifo_depletion(session, item, -quantity_delta)
    else:
        lot_payload = InventoryLotCreate(
            quantity=quantity_delta,
            unit=payload.unit or item.unit,
            expiry_date=payload.expiry_date,
            received_at=payload.received_at,
            source_reference=payload.source_reference,
        )
        session.add(_create_lot_from_payload(item, lot_payload))
        _recalculate_item(item)

    session.add(item)
    session.commit()
    session.refresh(item)
    return _serialize_item(item)


@app.post("/transfer", response_model=InventoryTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: InventoryTransferRequest,
    session: Session = Depends(_get_session),
) -> InventoryTransferResponse:
    item = session.get(InventoryItem, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.kitchen_id != payload.from_kitchen_id:
        raise HTTPException(status_code=400, detail="Item does not belong to source kitchen")
    if payload.unit != item.unit:
        raise HTTPException(status_code=400, detail="Unit mismatch for transfer")

    transfer = InventoryTransfer(
        item=item,
        from_kitchen_id=payload.from_kitchen_id,
        to_kitchen_id=payload.to_kitchen_id,
        requested_by_host_id=payload.requested_by_host_id,
        quantity=_to_decimal(payload.quantity),
        unit=payload.unit,
        notes=payload.notes,
        expiry_date=payload.expiry_date,
    )
    session.add(transfer)
    session.commit()
    session.refresh(transfer)
    return InventoryTransferResponse.model_validate(transfer)


def _find_or_create_receiving_item(
    session: Session,
    source_item: InventoryItem,
    to_kitchen_id: UUID,
    receiving_host_id: UUID,
) -> InventoryItem:
    stmt = (
        select(InventoryItem)
        .where(
            InventoryItem.kitchen_id == to_kitchen_id,
            InventoryItem.sku == source_item.sku,
            InventoryItem.name == source_item.name,
        )
        .options(joinedload(InventoryItem.lots))
    )
    receiving_item = session.execute(stmt).scalar_one_or_none()
    if receiving_item:
        return receiving_item

    receiving_item = InventoryItem(
        kitchen_id=to_kitchen_id,
        host_id=receiving_host_id,
        name=source_item.name,
        sku=source_item.sku,
        category=source_item.category,
        unit=source_item.unit,
        supplier=source_item.supplier,
        source=source_item.source,
    )
    session.add(receiving_item)
    session.flush()
    return receiving_item


@app.get("/transfer", response_model=List[InventoryTransferResponse])
async def list_transfers(
    status_filter: InventoryTransferStatus | None = Query(default=None, alias="status"),
    kitchen_id: UUID | None = Query(default=None),
    session: Session = Depends(_get_session),
) -> List[InventoryTransferResponse]:
    stmt = select(InventoryTransfer)
    if status_filter:
        stmt = stmt.where(InventoryTransfer.approval_status == status_filter)
    if kitchen_id:
        stmt = stmt.where(
            (InventoryTransfer.from_kitchen_id == kitchen_id)
            | (InventoryTransfer.to_kitchen_id == kitchen_id)
        )
    transfers = session.scalars(stmt).all()
    return [InventoryTransferResponse.model_validate(transfer) for transfer in transfers]


@app.patch("/transfer/{transfer_id}", response_model=InventoryTransferResponse)
async def update_transfer(
    transfer_id: UUID,
    payload: InventoryTransferUpdateRequest,
    session: Session = Depends(_get_session),
) -> InventoryTransferResponse:
    transfer = session.execute(
        select(InventoryTransfer)
        .where(InventoryTransfer.id == transfer_id)
        .options(joinedload(InventoryTransfer.item).joinedload(InventoryItem.lots))
    ).scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    previous_status = transfer.approval_status
    transfer.approval_status = payload.approval_status
    if payload.notes is not None:
        transfer.notes = payload.notes

    if payload.approved_by_host_id is not None:
        transfer.approved_by_host_id = payload.approved_by_host_id

    if (
        previous_status != InventoryTransferStatus.APPROVED
        and payload.approval_status == InventoryTransferStatus.APPROVED
    ):
        transfer.approved_at = datetime.now(UTC)
        consumed_expiry = _apply_fifo_depletion(session, transfer.item, transfer.quantity)
        receiving_item = _find_or_create_receiving_item(
            session,
            transfer.item,
            transfer.to_kitchen_id,
            transfer.requested_by_host_id,
        )
        lot_payload = InventoryLotCreate(
            quantity=transfer.quantity,
            unit=transfer.unit,
            expiry_date=transfer.expiry_date or consumed_expiry,
        )
        session.add(_create_lot_from_payload(receiving_item, lot_payload))
        _recalculate_item(receiving_item)
        session.add(receiving_item)
    elif payload.approval_status in {
        InventoryTransferStatus.DECLINED,
        InventoryTransferStatus.CANCELLED,
    }:
        transfer.approved_at = None

    session.add(transfer)
    session.commit()
    session.refresh(transfer)
    return InventoryTransferResponse.model_validate(transfer)


__all__ = ["app"]
