"""QuickBooks connector focused on revenue summaries and expenses."""

from __future__ import annotations

from typing import Sequence

from prep.accounting.schemas import DailyRevenueSummary, ExpenseCategory
from prep.accounting.service import GAAPLedgerService


class QuickBooksConnector:
    """High-level helper for orchestrating QuickBooks data syncs."""

    def __init__(self, service: GAAPLedgerService) -> None:
        self._service = service

    async def push_daily_revenue_summaries(
        self, summaries: Sequence[DailyRevenueSummary]
    ) -> int:
        """Push normalized revenue summaries into the GAAP ledger."""

        processed = 0
        for summary in summaries:
            await self._service.record_revenue_summary(summary, source="quickbooks")
            processed += 1
        return processed

    async def sync_expense_categories(
        self, categories: Sequence[ExpenseCategory]
    ) -> int:
        """Sync QuickBooks expense categories into the ledger."""

        for category in categories:
            await self._service.sync_expense_category(category, source="quickbooks")
        return len(categories)


__all__ = ["QuickBooksConnector"]
