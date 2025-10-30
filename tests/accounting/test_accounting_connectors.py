from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from integrations.accounting import QuickBooksConnector, XeroConnector
from prep.accounting.schemas import (
    DailyRevenueSummary,
    ExpenseCategory,
    InvoicePayload,
    PaymentRecord,
    VendorExpense,
)
from prep.accounting.service import GAAPLedgerService
from prep.models.orm import Base, LedgerEntry, RevenueType


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
async def test_quickbooks_connector_syncs_revenue_and_expenses(session: AsyncSession) -> None:
    service = GAAPLedgerService(session)
    connector = QuickBooksConnector(service)
    booking_id = uuid4()

    summaries = [
        DailyRevenueSummary(
            booking_id=booking_id,
            date=date(2024, 4, 1),
            total_amount=Decimal("200.00"),
            currency="usd",
            description="Shared shelf rental",
            channel="Shared Shelf",
            external_reference="QB-REV-1",
        ),
        DailyRevenueSummary(
            booking_id=uuid4(),
            date=date(2024, 4, 1),
            total_amount=Decimal("350.00"),
            currency="usd",
            description="Delivery program revenue",
            channel="Delivery",
            external_reference="QB-REV-2",
        ),
    ]

    processed = await connector.push_daily_revenue_summaries(summaries)
    assert processed == len(summaries)

    expense_count = await connector.sync_expense_categories(
        [
            ExpenseCategory(
                category_name="Supplies",
                account="COGS",
                amount=Decimal("42.00"),
                currency="usd",
                effective_date=date(2024, 4, 2),
                booking_id=booking_id,
            )
        ]
    )
    assert expense_count == 1

    entries = await session.execute(select(LedgerEntry))
    rows = entries.scalars().all()
    assert len(rows) == 2
    by_reference = {row.external_reference: row for row in rows}
    assert by_reference["QB-REV-1"].revenue_type is RevenueType.SHARED_SHELF
    assert by_reference["QB-REV-1"].expense_category == "Supplies"
    assert by_reference["QB-REV-2"].revenue_type is RevenueType.DELIVERY


@pytest.mark.asyncio
async def test_xero_connector_syncs_documents(session: AsyncSession) -> None:
    service = GAAPLedgerService(session)
    connector = XeroConnector(service)
    booking_id = uuid4()

    invoices = [
        InvoicePayload(
            invoice_id="INV-1001",
            booking_id=booking_id,
            amount_due=Decimal("480.00"),
            issued_at=datetime(2024, 5, 1, 10, 30),
            due_at=datetime(2024, 5, 15, 10, 30),
            currency="usd",
        )
    ]
    payments = [
        PaymentRecord(
            payment_id="PAY-1001",
            invoice_id="INV-1001",
            booking_id=booking_id,
            amount_paid=Decimal("480.00"),
            paid_at=datetime(2024, 5, 2, 9, 0),
            currency="usd",
        )
    ]
    expenses = [
        VendorExpense(
            expense_id="EXP-5001",
            vendor_name="Fresh Supply Co",
            amount=Decimal("125.00"),
            category="Supplies",
            incurred_on=date(2024, 5, 3),
            booking_id=booking_id,
            currency="usd",
        )
    ]

    await connector.sync_invoices(invoices)
    await connector.sync_payments(payments)
    await connector.sync_vendor_expenses(expenses)

    result = await session.execute(select(LedgerEntry).where(LedgerEntry.source == "xero"))
    entries = result.scalars().all()
    assert {entry.external_reference for entry in entries} == {"INV-1001", "PAY-1001", "EXP-5001"}
    assert {entry.debit_account for entry in entries} >= {"Cash", "Accounts Receivable", "Supplies"}
