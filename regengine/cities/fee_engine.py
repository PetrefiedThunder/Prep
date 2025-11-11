"""
Municipal Fee and Tax Computation Engine

Computes city/county-specific fees, taxes, deposits, and late penalties
with deterministic, auditable calculations.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, UTC
import yaml
import os


class FeeLineItem:
    """A single fee/tax line item."""

    def __init__(
        self,
        code: str,
        display_name: str,
        kind: str,
        value: Decimal,
        base_amount_cents: int,
        computed_fee_cents: int,
        citation: Optional[str] = None
    ):
        self.code = code
        self.display_name = display_name
        self.kind = kind
        self.value = value
        self.base_amount_cents = base_amount_cents
        self.computed_fee_cents = computed_fee_cents
        self.citation = citation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "display_name": self.display_name,
            "kind": self.kind,
            "value": float(self.value),
            "base_amount_cents": self.base_amount_cents,
            "computed_fee_cents": self.computed_fee_cents,
            "citation": self.citation
        }


class FeeQuote:
    """Complete fee/tax/deposit quote for a booking."""

    def __init__(self, jurisdiction_id: str):
        self.jurisdiction_id = jurisdiction_id
        self.line_items: List[FeeLineItem] = []
        self.deposit_cents: int = 0
        self.deposit_hold_window_hours: int = 72
        self.late_penalty_cents: int = 0
        self.total_fees_cents: int = 0
        self.total_cents: int = 0
        self.computed_at: datetime = datetime.now(UTC)

    def add_line_item(self, item: FeeLineItem):
        """Add a fee line item."""
        self.line_items.append(item)
        self.total_fees_cents += item.computed_fee_cents
        self._recalculate_total()

    def set_deposit(self, cents: int, hold_window_hours: int = 72):
        """Set security deposit."""
        self.deposit_cents = cents
        self.deposit_hold_window_hours = hold_window_hours
        self._recalculate_total()

    def set_late_penalty(self, cents: int):
        """Set late payment penalty."""
        self.late_penalty_cents = cents
        self._recalculate_total()

    def _recalculate_total(self):
        """Recalculate total amount."""
        self.total_cents = (
            self.total_fees_cents +
            self.deposit_cents +
            self.late_penalty_cents
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jurisdiction_id": self.jurisdiction_id,
            "line_items": [item.to_dict() for item in self.line_items],
            "deposit_cents": self.deposit_cents,
            "deposit_hold_window_hours": self.deposit_hold_window_hours,
            "late_penalty_cents": self.late_penalty_cents,
            "total_fees_cents": self.total_fees_cents,
            "total_cents": self.total_cents,
            "computed_at": self.computed_at.isoformat()
        }


class MunicipalFeeEngine:
    """
    Computes municipal fees, taxes, deposits, and penalties.

    Usage:
        engine = MunicipalFeeEngine("san_francisco")
        quote = engine.compute_fee_quote(
            line_items=[
                {"code": "base", "cents": 19500},
                {"code": "cleaning", "cents": 2500},
                {"code": "platform_fee", "cents": 2200}
            ],
            booking_id="...",
            created_at=datetime.now(UTC)
        )
    """

    def __init__(self, jurisdiction_id: str, config_path: Optional[str] = None):
        self.jurisdiction_id = jurisdiction_id

        # Load city config
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                jurisdiction_id,
                "config.yaml"
            )

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.fees = self.config.get('fees', [])
        self.deposits_config = self.config.get('deposits', {})

    def compute_fee_quote(
        self,
        line_items: List[Dict[str, Any]],
        booking_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        confirmed_at: Optional[datetime] = None
    ) -> FeeQuote:
        """
        Compute complete fee quote for a booking.

        Args:
            line_items: List of {code, cents} dicts (e.g., base, cleaning, platform_fee)
            booking_id: Booking identifier (for audit trail)
            created_at: When booking was created
            confirmed_at: When booking was confirmed (for late penalty calc)

        Returns:
            FeeQuote with all computed fees, taxes, deposits, penalties
        """
        quote = FeeQuote(self.jurisdiction_id)

        # Build line item map
        line_item_map = {item['code']: item['cents'] for item in line_items}

        # Compute each fee/tax
        for fee_config in self.fees:
            fee_item = self._compute_fee(fee_config, line_item_map)
            if fee_item:
                quote.add_line_item(fee_item)

        # Compute security deposit
        deposit_cents = self._compute_deposit(line_items)
        deposit_hold_hours = self.deposits_config.get('hold_window_hours', 72)
        quote.set_deposit(deposit_cents, deposit_hold_hours)

        # Compute late penalty if applicable
        if created_at and confirmed_at:
            late_penalty = self._compute_late_penalty(created_at, confirmed_at)
            if late_penalty > 0:
                quote.set_late_penalty(late_penalty)

        return quote

    def _compute_fee(
        self,
        fee_config: Dict[str, Any],
        line_item_map: Dict[str, int]
    ) -> Optional[FeeLineItem]:
        """Compute a single fee/tax line item."""
        code = fee_config['code']
        display_name = fee_config['display_name']
        kind = fee_config['kind']
        value = Decimal(str(fee_config['value']))
        applies_to = fee_config['applies_to']
        citation = fee_config.get('citation')

        # Sum up base amounts this fee applies to
        base_amount_cents = sum(
            line_item_map.get(component, 0)
            for component in applies_to
        )

        if base_amount_cents == 0:
            return None

        # Compute fee based on kind
        if kind == 'percent':
            # Multiply base by percentage, round to nearest cent
            computed_cents = int(
                (Decimal(base_amount_cents) * value).quantize(
                    Decimal('1'), rounding=ROUND_HALF_UP
                )
            )
        elif kind == 'flat_per_booking':
            computed_cents = int(value)
        elif kind == 'flat_per_hour':
            # Would need booking duration - not implemented yet
            computed_cents = 0
        else:
            computed_cents = 0

        return FeeLineItem(
            code=code,
            display_name=display_name,
            kind=kind,
            value=value,
            base_amount_cents=base_amount_cents,
            computed_fee_cents=computed_cents,
            citation=citation
        )

    def _compute_deposit(self, line_items: List[Dict[str, Any]]) -> int:
        """Compute security deposit."""
        min_deposit = self.deposits_config.get('min_cents', 10000)

        # For now, just return minimum
        # Could implement percentage-of-booking logic here
        return min_deposit

    def _compute_late_penalty(
        self,
        created_at: datetime,
        confirmed_at: datetime
    ) -> int:
        """
        Compute late confirmation penalty.

        Example: If booking not confirmed within 24h, 5% penalty.
        """
        # Placeholder - would load from late_penalty_policies table
        # or config file

        delay_hours = (confirmed_at - created_at).total_seconds() / 3600

        if delay_hours > 24:
            # 5% penalty, max $50
            # Would need base amount - simplified for now
            return 0

        return 0

    def get_deposit_policy(self) -> Dict[str, Any]:
        """Get deposit policy for jurisdiction."""
        return {
            "min_cents": self.deposits_config.get('min_cents', 10000),
            "max_cents": self.deposits_config.get('max_cents'),
            "hold_window_hours": self.deposits_config.get('hold_window_hours', 72),
            "refund_window_hours": self.deposits_config.get('refund_window_hours', 168)
        }


# Example usage
if __name__ == "__main__":
    # San Francisco example
    engine = MunicipalFeeEngine("san_francisco")

    quote = engine.compute_fee_quote(
        line_items=[
            {"code": "base", "cents": 19500},        # $195 base rate
            {"code": "cleaning", "cents": 2500},     # $25 cleaning
            {"code": "platform_fee", "cents": 2200}  # $22 platform fee
        ]
    )

    print(f"Jurisdiction: {quote.jurisdiction_id}")
    print(f"\nFees/Taxes:")
    for item in quote.line_items:
        print(f"  {item.display_name}: ${item.computed_fee_cents / 100:.2f}")
        print(f"    ({item.value * 100}% of ${item.base_amount_cents / 100:.2f})")

    print(f"\nDeposit: ${quote.deposit_cents / 100:.2f}")
    print(f"Hold window: {quote.deposit_hold_window_hours} hours")
    print(f"\nTotal fees: ${quote.total_fees_cents / 100:.2f}")
    print(f"Total amount: ${quote.total_cents / 100:.2f}")
