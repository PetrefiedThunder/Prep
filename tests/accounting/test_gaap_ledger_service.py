from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prep.accounting.schemas import (
    BookingTaxRequest,
    DailyRevenueSummary,
    ExpenseCategory,
    LedgerExportFormat,
)
from prep.accounting.service import GAAPLedgerService
from prep.models.orm import Base, RevenueType


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_revenue_summary_classifies(session: AsyncSession) -> None:
    service = GAAPLedgerService(session)
    summary = DailyRevenueSummary(
        booking_id=uuid4(),
        date=date(2024, 1, 5),
        total_amount=Decimal("125.50"),
        currency="usd",
        description="Delivery catering order",
        channel="Delivery App",
        external_reference="QB-1",
    )

    entry = await service.record_revenue_summary(summary, source="quickbooks")
    assert entry.revenue_type is RevenueType.DELIVERY

    export = await service.export_ledger(format=LedgerExportFormat.JSON)
    rows = json.loads(export.content)
    assert rows[0]["revenue_type"] == RevenueType.DELIVERY.value


@pytest.mark.asyncio
async def test_expense_category_updates_existing_entry(session: AsyncSession) -> None:
    service = GAAPLedgerService(session)
    booking_id = uuid4()
    summary = DailyRevenueSummary(
        booking_id=booking_id,
        date=date(2024, 2, 1),
        total_amount=Decimal("80.00"),
        currency="usd",
        description="Shared shelf rental",
        channel="Shared Shelf",
        external_reference="QB-2",
    )
    await service.record_revenue_summary(summary, source="quickbooks")

    expense = ExpenseCategory(
        category_name="Cleaning Supplies",
        account="COGS",
        amount=Decimal("18.25"),
        currency="usd",
        effective_date=date(2024, 2, 2),
        booking_id=booking_id,
    )

    entry = await service.sync_expense_category(expense, source="quickbooks")
    assert entry.expense_category == "Cleaning Supplies"
    assert entry.details["expense_account"] == "COGS"


@pytest.mark.asyncio
async def test_calculate_and_store_tax(session: AsyncSession) -> None:
    service = GAAPLedgerService(session)
    booking_id = uuid4()

    summary = DailyRevenueSummary(
        booking_id=booking_id,
        date=date(2024, 3, 10),
        total_amount=Decimal("150.00"),
        currency="usd",
        description="Booking reservation",
        channel="Platform",
        external_reference="QB-3",
    )
    await service.record_revenue_summary(summary, source="quickbooks")

    request = BookingTaxRequest(
        booking_id=booking_id,
        jurisdiction="CA",
        taxable_amount=Decimal("150.00"),
        currency="usd",
    )

    record = await service.calculate_and_store_tax(request)
    assert record.tax_amount > Decimal("0")
    assert record.jurisdiction == "CA"
