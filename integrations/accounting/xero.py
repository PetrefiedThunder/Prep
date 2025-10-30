"""Xero connector responsible for syncing invoices, payments, and expenses."""

from __future__ import annotations

from typing import Sequence

from prep.accounting.schemas import InvoicePayload, PaymentRecord, VendorExpense
from prep.accounting.service import GAAPLedgerService


class XeroConnector:
    """Coordinates Xero objects with the GAAP ledger service."""

    def __init__(self, service: GAAPLedgerService) -> None:
        self._service = service

    async def sync_invoices(self, invoices: Sequence[InvoicePayload]) -> int:
        """Sync invoices from Xero into the GAAP ledger."""

        for invoice in invoices:
            await self._service.sync_invoice(invoice, source="xero")
        return len(invoices)

    async def sync_payments(self, payments: Sequence[PaymentRecord]) -> int:
        """Persist payments that have been settled in Xero."""

        for payment in payments:
            await self._service.sync_payment(payment, source="xero")
        return len(payments)

    async def sync_vendor_expenses(self, expenses: Sequence[VendorExpense]) -> int:
        """Push vendor expenses recorded in Xero into the ledger."""

        for expense in expenses:
            await self._service.sync_vendor_expense(expense, source="xero")
        return len(expenses)


__all__ = ["XeroConnector"]
