"""Lightweight Avalara API adapter for sales tax lookups."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from prep.accounting.schemas import BookingTaxRequest, TaxComputationResult

_DEFAULT_RATE = Decimal("0.0825")
_DEFAULT_BREAKDOWN = {
    "state": Decimal("0.0500"),
    "county": Decimal("0.0225"),
    "city": Decimal("0.0100"),
}


class AvalaraClient:
    """Deterministic Avalara adapter used for tests and local development."""

    def __init__(self, *, rate_overrides: Mapping[str, Decimal] | None = None) -> None:
        self._rates = {key.upper(): value for key, value in (rate_overrides or {}).items()}

    async def map_tax(self, request: BookingTaxRequest) -> TaxComputationResult:
        """Return a jurisdiction-specific tax computation."""

        jurisdiction = request.jurisdiction.upper()
        rate = self._rates.get(jurisdiction, _DEFAULT_RATE)
        taxable_amount = request.taxable_amount
        tax_amount = (taxable_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Proportionally scale the default breakdown to the computed rate.
        base_total = sum(_DEFAULT_BREAKDOWN.values()) or Decimal("1")
        breakdown = {
            key: (tax_amount * (portion / base_total)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            for key, portion in _DEFAULT_BREAKDOWN.items()
        }

        return TaxComputationResult(
            booking_id=request.booking_id,
            jurisdiction=jurisdiction,
            tax_rate=rate.quantize(Decimal("0.0001")),
            taxable_amount=taxable_amount,
            tax_amount=tax_amount,
            currency=request.currency,
            breakdown=breakdown,
        )


__all__ = ["AvalaraClient"]
