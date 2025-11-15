"""Shared data models for accounting connectors and services."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LedgerExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"


class DailyRevenueSummary(BaseModel):
    """Normalized representation of daily revenue totals."""

    booking_id: UUID | None = Field(default=None)
    revenue_date: date = Field(default_factory=date.today)
    total_amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str = Field(min_length=1)
    channel: str | None = Field(default=None)
    external_reference: str | None = Field(default=None, max_length=120)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class ExpenseCategory(BaseModel):
    """Metadata describing how an expense should be classified."""

    category_name: str = Field(min_length=1, max_length=120)
    account: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    effective_date: date = Field(default_factory=date.today)
    booking_id: UUID | None = Field(default=None)
    ledger_entry_id: UUID | None = Field(default=None)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class InvoicePayload(BaseModel):
    """Minimal invoice structure required for ledger postings."""

    invoice_id: str = Field(min_length=1, max_length=120)
    booking_id: UUID
    amount_due: Decimal = Field(gt=Decimal("0"))
    issued_at: datetime
    due_at: datetime
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class PaymentRecord(BaseModel):
    """Represents a payment applied to an invoice or booking."""

    payment_id: str = Field(min_length=1, max_length=120)
    invoice_id: str | None = Field(default=None, max_length=120)
    booking_id: UUID
    amount_paid: Decimal = Field(gt=Decimal("0"))
    paid_at: datetime
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class VendorExpense(BaseModel):
    """Vendor expense metadata flowing in from accounting connectors."""

    expense_id: str = Field(min_length=1, max_length=120)
    vendor_name: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=Decimal("0"))
    category: str = Field(min_length=1, max_length=120)
    incurred_on: date = Field(default_factory=date.today)
    booking_id: UUID | None = Field(default=None)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class BookingTaxRequest(BaseModel):
    """Request payload for calculating sales tax on a booking."""

    booking_id: UUID
    jurisdiction: str = Field(min_length=2, max_length=120)
    taxable_amount: Decimal = Field(ge=Decimal("0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    item_code: str | None = Field(default=None, max_length=120)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.upper()


class TaxComputationResult(BaseModel):
    """Response returned after applying Avalara tax mapping."""

    booking_id: UUID
    jurisdiction: str
    tax_rate: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    currency: str
    breakdown: dict[str, Decimal]


class LedgerExport(BaseModel):
    """Normalized export payload returned by the ledger service."""

    format: LedgerExportFormat
    content: str
    generated_at: datetime


__all__ = [
    "DailyRevenueSummary",
    "ExpenseCategory",
    "InvoicePayload",
    "PaymentRecord",
    "VendorExpense",
    "LedgerExport",
    "LedgerExportFormat",
    "BookingTaxRequest",
    "TaxComputationResult",
]
