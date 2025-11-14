"""Service objects orchestrating GAAP ledger workflows."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.models.orm import LedgerEntry, RevenueType, TaxRecord

from .schemas import (
    BookingTaxRequest,
    DailyRevenueSummary,
    ExpenseCategory,
    InvoicePayload,
    LedgerExport,
    LedgerExportFormat,
    PaymentRecord,
    TaxComputationResult,
    VendorExpense,
)


class AvalaraClientProtocol:
    """Protocol-style duck type for Avalara API adapters."""

    async def map_tax(
        self, request: BookingTaxRequest
    ) -> TaxComputationResult:  # pragma: no cover - protocol definition
        ...


class GAAPLedgerService:
    """Coordinates ledger activity across accounting connectors and tax mapping."""

    def __init__(
        self,
        session: AsyncSession,
        avalara_client: AvalaraClientProtocol | None = None,
    ) -> None:
        from integrations.accounting.avalara import AvalaraClient

        self._session = session
        self._avalara = avalara_client or AvalaraClient()

    async def record_revenue_summary(
        self,
        summary: DailyRevenueSummary,
        *,
        source: str,
    ) -> LedgerEntry:
        """Persist a summary revenue record into the GAAP ledger."""

        revenue_type = self._classify_revenue(summary)
        entry = LedgerEntry(
            booking_id=summary.booking_id,
            source=source,
            entry_date=summary.date,
            description=summary.description,
            debit_account="Accounts Receivable",
            credit_account=f"{revenue_type.value}_revenue",
            amount=summary.total_amount,
            currency=summary.currency,
            revenue_type=revenue_type,
            expense_category=None,
            external_reference=summary.external_reference,
            details=self._build_details(
                {
                    "channel": summary.channel,
                    "summary_type": "daily_revenue",
                }
            ),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def sync_expense_category(
        self,
        category: ExpenseCategory,
        *,
        source: str,
    ) -> LedgerEntry:
        """Apply an expense category to an existing ledger entry or create one."""

        entry = None
        if category.ledger_entry_id is not None:
            entry = await self._session.get(LedgerEntry, category.ledger_entry_id)
        elif category.booking_id is not None:
            stmt: Select[LedgerEntry] = (
                select(LedgerEntry)
                .where(LedgerEntry.booking_id == category.booking_id)
                .order_by(LedgerEntry.entry_date.desc(), LedgerEntry.created_at.desc())
            )
            existing = await self._session.execute(stmt)
            entry = existing.scalars().first()

        if entry is not None:
            entry.expense_category = category.category_name
            entry.currency = category.currency
            details = dict(entry.details or {})
            details.update(
                {
                    "expense_account": category.account,
                    "expense_amount": str(category.amount),
                    "expense_source": source,
                }
            )
            entry.details = details
            await self._session.flush()
            return entry

        entry = LedgerEntry(
            booking_id=category.booking_id,
            source=source,
            entry_date=category.effective_date,
            description=f"Expense: {category.category_name}",
            debit_account=category.account,
            credit_account="Accounts Payable",
            amount=category.amount,
            currency=category.currency,
            revenue_type=None,
            expense_category=category.category_name,
            external_reference=None,
            details=self._build_details(
                {
                    "category": category.category_name,
                    "expense_source": source,
                }
            ),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def sync_invoice(
        self,
        invoice: InvoicePayload,
        *,
        source: str,
    ) -> LedgerEntry:
        """Create a ledger entry representing an issued invoice."""

        entry = LedgerEntry(
            booking_id=invoice.booking_id,
            source=source,
            entry_date=invoice.issued_at.date(),
            description=f"Invoice {invoice.invoice_id}",
            debit_account="Accounts Receivable",
            credit_account="Deferred Revenue",
            amount=invoice.amount_due,
            currency=invoice.currency,
            revenue_type=None,
            expense_category=None,
            external_reference=invoice.invoice_id,
            details=self._build_details(
                {
                    "due_at": invoice.due_at.isoformat(),
                }
            ),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def sync_payment(
        self,
        payment: PaymentRecord,
        *,
        source: str,
    ) -> LedgerEntry:
        """Persist a payment entry tied back to the booking or invoice."""

        entry = LedgerEntry(
            booking_id=payment.booking_id,
            source=source,
            entry_date=payment.paid_at.date(),
            description=f"Payment {payment.payment_id}",
            debit_account="Cash",
            credit_account="Accounts Receivable",
            amount=payment.amount_paid,
            currency=payment.currency,
            revenue_type=None,
            expense_category=None,
            external_reference=payment.payment_id,
            details=self._build_details(
                {
                    "invoice_id": payment.invoice_id,
                }
            ),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def sync_vendor_expense(
        self,
        expense: VendorExpense,
        *,
        source: str,
    ) -> LedgerEntry:
        """Create a ledger entry for a vendor expense."""

        entry = LedgerEntry(
            booking_id=expense.booking_id,
            source=source,
            entry_date=expense.incurred_on,
            description=f"Vendor expense {expense.vendor_name}",
            debit_account=expense.category,
            credit_account="Accounts Payable",
            amount=expense.amount,
            currency=expense.currency,
            revenue_type=None,
            expense_category=expense.category,
            external_reference=expense.expense_id,
            details=self._build_details(
                {
                    "vendor": expense.vendor_name,
                }
            ),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def calculate_and_store_tax(
        self,
        request: BookingTaxRequest,
    ) -> TaxRecord:
        """Calculate booking tax via Avalara and persist the normalized result."""

        result = await self._avalara.map_tax(request)

        existing = await self._session.execute(
            select(TaxRecord).where(
                (TaxRecord.booking_id == result.booking_id)
                & (TaxRecord.jurisdiction == result.jurisdiction)
            )
        )
        record = existing.scalars().first()

        details = {key: str(value) for key, value in result.breakdown.items()}

        if record is None:
            record = TaxRecord(
                booking_id=result.booking_id,
                jurisdiction=result.jurisdiction,
                tax_rate=result.tax_rate,
                taxable_amount=result.taxable_amount,
                tax_amount=result.tax_amount,
                currency=result.currency,
                details=details,
            )
            self._session.add(record)
        else:
            record.tax_rate = result.tax_rate
            record.taxable_amount = result.taxable_amount
            record.tax_amount = result.tax_amount
            record.currency = result.currency
            record.details = details

        await self._session.flush()
        return record

    async def export_ledger(
        self,
        *,
        format: LedgerExportFormat | str = LedgerExportFormat.JSON,
    ) -> LedgerExport:
        """Render the ledger as either CSV or JSON for downstream systems."""

        if isinstance(format, str):
            format = LedgerExportFormat(format.lower())

        stmt = select(LedgerEntry).order_by(
            LedgerEntry.entry_date.asc(), LedgerEntry.created_at.asc()
        )
        result = await self._session.execute(stmt)
        entries = result.scalars().all()
        rows = [self._entry_to_dict(entry) for entry in entries]

        if format is LedgerExportFormat.JSON:
            content = json.dumps(rows, ensure_ascii=False)
        else:
            output = io.StringIO()
            fieldnames = [
                "entry_date",
                "description",
                "debit_account",
                "credit_account",
                "amount",
                "currency",
                "revenue_type",
                "source",
                "expense_category",
                "external_reference",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in fieldnames})
            content = output.getvalue()

        return LedgerExport(
            format=format,
            content=content,
            generated_at=datetime.now(UTC),
        )

    def _entry_to_dict(self, entry: LedgerEntry) -> dict[str, str]:
        """Serialize a ledger entry for export."""

        return {
            "entry_date": entry.entry_date.isoformat(),
            "description": entry.description,
            "debit_account": entry.debit_account,
            "credit_account": entry.credit_account,
            "amount": f"{entry.amount:.2f}",
            "currency": entry.currency,
            "revenue_type": entry.revenue_type.value if entry.revenue_type else "",
            "source": entry.source,
            "expense_category": entry.expense_category or "",
            "external_reference": entry.external_reference or "",
        }

    def _classify_revenue(self, summary: DailyRevenueSummary) -> RevenueType:
        """Infer the GAAP revenue type from description metadata."""

        tokens = " ".join(
            token for token in [summary.channel or "", summary.description] if token
        ).lower()
        if "delivery" in tokens:
            return RevenueType.DELIVERY
        if "shelf" in tokens or "shared" in tokens:
            return RevenueType.SHARED_SHELF
        return RevenueType.BOOKING

    def _build_details(self, payload: dict[str, str | None]) -> dict[str, str]:
        """Create a JSON-serializable payload that omits null values."""

        return {key: value for key, value in payload.items() if value is not None}


__all__ = ["GAAPLedgerService"]
