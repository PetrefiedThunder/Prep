"""Fee schedule models and helpers used by jurisdiction scrapers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

__all__ = [
    "FeeItem",
    "FeeSchedule",
    "FeeValidationResult",
    "validate_fee_schedule",
    "make_fee_schedule",
    "total_one_time_cents",
    "total_recurring_annualized_cents",
    "has_incremental",
]

# ---------------------------------------------------------------------------
# Supported fee metadata
# ---------------------------------------------------------------------------

_VALID_KINDS: set[str] = {"one_time", "recurring", "incremental"}
_VALID_CADENCE: dict[str, int] = {
    "annual": 1,
    "semi_annual": 2,
    "quarterly": 4,
    "monthly": 12,
}
_INCREMENTAL_UNITS: set[str] = {
    "per_permit",
    "per_inspection",
    "per_application",
    "per_reinspection",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FeeItem:
    """Represents a single fee entry."""

    name: str
    amount_cents: int
    kind: str
    cadence: Optional[str] = None
    unit: Optional[str] = None
    tier_min_inclusive: Optional[int] = None
    tier_max_inclusive: Optional[int] = None

    def dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation."""

        return {
            "name": self.name,
            "amount_cents": self.amount_cents,
            "kind": self.kind,
            "cadence": self.cadence,
            "unit": self.unit,
            "tier_min_inclusive": self.tier_min_inclusive,
            "tier_max_inclusive": self.tier_max_inclusive,
        }

    def annualized_amount_cents(self) -> int:
        """Return the annualized cents value for recurring fees."""

        if self.kind != "recurring":
            return 0
        cadence = self.cadence or "annual"
        multiplier = _VALID_CADENCE.get(cadence, 0)
        return self.amount_cents * multiplier


@dataclass(slots=True)
class FeeSchedule:
    """Represents the full fee schedule for a jurisdiction."""

    jurisdiction: str
    paperwork: list[str] = field(default_factory=list)
    fees: list[FeeItem] = field(default_factory=list)

    @property
    def total_one_time_cents(self) -> int:
        return sum(f.amount_cents for f in self.fees if f.kind == "one_time")

    @property
    def total_recurring_annualized_cents(self) -> int:
        return sum(f.annualized_amount_cents() for f in self.fees if f.kind == "recurring")


@dataclass(slots=True)
class FeeValidationResult:
    """Validation summary for a fee schedule."""

    is_valid: bool
    issues: list[str]
    incremental_fee_count: int


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_fee_schedule(schedule: FeeSchedule) -> FeeValidationResult:
    """Validate a fee schedule returning any issues discovered."""

    issues: list[str] = []

    if not schedule.jurisdiction:
        issues.append("Missing jurisdiction identifier")

    if not schedule.fees:
        issues.append("Fee schedule must include at least one fee")

    incremental_count = 0

    for idx, fee in enumerate(schedule.fees):
        if fee.kind not in _VALID_KINDS:
            issues.append(f"Fee #{idx + 1} has invalid kind '{fee.kind}'")
        if fee.amount_cents < 0:
            issues.append(f"Fee '{fee.name}' must have a non-negative amount")

        if fee.kind == "recurring":
            cadence = fee.cadence or "annual"
            if cadence not in _VALID_CADENCE:
                issues.append(f"Recurring fee '{fee.name}' has unsupported cadence '{cadence}'")

        if fee.kind == "incremental":
            incremental_count += 1
            if fee.unit and fee.unit not in _INCREMENTAL_UNITS:
                issues.append(f"Incremental fee '{fee.name}' has unsupported unit '{fee.unit}'")

        if (
            fee.tier_min_inclusive is not None
            and fee.tier_max_inclusive is not None
            and fee.tier_min_inclusive > fee.tier_max_inclusive
        ):
            issues.append(
                f"Fee '{fee.name}' has inconsistent tier bounds"
                f" ({fee.tier_min_inclusive} > {fee.tier_max_inclusive})"
            )

    return FeeValidationResult(
        is_valid=not issues,
        issues=issues,
        incremental_fee_count=incremental_count,
    )


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------

def make_fee_schedule(
    jurisdiction: str,
    paperwork: Optional[Iterable[str]] = None,
    fees: Optional[Iterable[FeeItem]] = None,
) -> FeeSchedule:
    """Helper to quickly build a fee schedule instance."""

    return FeeSchedule(
        jurisdiction=jurisdiction,
        paperwork=list(paperwork or []),
        fees=list(fees or []),
    )


def _coerce_iterable(items: FeeSchedule | Iterable[FeeItem]) -> Iterable[FeeItem]:
    if isinstance(items, FeeSchedule):
        return items.fees
    return items


def total_one_time_cents(items: FeeSchedule | Iterable[FeeItem]) -> int:
    """Compute the total of one-time fees (in cents)."""

    return sum(item.amount_cents for item in _coerce_iterable(items) if item.kind == "one_time")


def total_recurring_annualized_cents(items: FeeSchedule | Iterable[FeeItem]) -> int:
    """Compute the total recurring fees normalised to an annual amount."""

    return sum(item.annualized_amount_cents() for item in _coerce_iterable(items))


def has_incremental(items: FeeSchedule | Iterable[FeeItem]) -> bool:
    """Return True if any fee item is marked as incremental."""

    return any(item.kind == "incremental" for item in _coerce_iterable(items))
