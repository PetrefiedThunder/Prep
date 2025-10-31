"""Fee schedule models and helpers used by jurisdiction scrapers."""
from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar, Literal, Sequence

from pydantic import BaseModel, Field, validator

RecurringInterval = Literal[
    "annual",
    "yearly",
    "semiannual",
    "quarterly",
    "monthly",
    "weekly",
    "daily",
    "biennial",
]


class FeeItem(BaseModel):
    """Represents a single fee entry for a jurisdiction."""

    label: str = Field(..., description="Human-readable label for the fee item")
    notes: str | None = Field(None, description="Additional context about the fee")
    one_time_cents: int | None = Field(
        None,
        ge=0,
        description="One-time amount charged for the fee (in cents)",
    )
    recurring_cents: int | None = Field(
        None,
        ge=0,
        description="Recurring amount charged for the fee (in cents)",
    )
    recurring_interval: RecurringInterval | None = Field(
        None,
        description="Interval describing how often the recurring amount is charged",
    )
    incremental: bool = Field(
        False,
        description="Whether the fee increases with quantity (per application, employee, etc.)",
    )

    _ANNUALIZATION_FACTORS: ClassVar[dict[str, float]] = {
        "annual": 1.0,
        "yearly": 1.0,
        "semiannual": 2.0,
        "quarterly": 4.0,
        "monthly": 12.0,
        "weekly": 52.0,
        "daily": 365.0,
        "biennial": 0.5,
    }

    @validator("recurring_interval")
    def _validate_interval_for_recurring_amount(
        cls, value: RecurringInterval | None, values: dict[str, object]
    ) -> RecurringInterval | None:
        recurring_cents = values.get("recurring_cents")
        if value is None and recurring_cents not in (None, 0):
            raise ValueError("recurring_interval is required when recurring_cents is provided")
        if value is not None and recurring_cents in (None, 0):
            raise ValueError("recurring_cents is required when recurring_interval is provided")
        return value

    def annualized_recurring_cents(self) -> int:
        """Return the recurring amount normalized to an annual amount."""

        if not self.recurring_cents or not self.recurring_interval:
            return 0
        factor = self._ANNUALIZATION_FACTORS.get(self.recurring_interval, 0)
        return int(self.recurring_cents * factor)


class FeeSchedule(BaseModel):
    """Collection of fee items applicable to a jurisdiction."""

    items: list[FeeItem] = Field(default_factory=list)
    notes: str | None = Field(None, description="Global notes about the fee schedule")

    @validator("items", each_item=False)
    def _ensure_unique_labels(cls, value: Sequence[FeeItem]) -> Sequence[FeeItem]:
        labels = [item.label for item in value]
        if len(labels) != len(set(labels)):
            raise ValueError("Fee item labels must be unique within a schedule")
        return value


class FeeValidationResult(BaseModel):
    """Represents the outcome of validating a fee schedule."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def validate_fee_schedule(schedule: FeeSchedule) -> FeeValidationResult:
    """Validate a fee schedule and collect any issues discovered."""

    errors: list[str] = []
    warnings: list[str] = []

    for idx, item in enumerate(schedule.items):
        context = f"item[{idx}] '{item.label}'"

        if (item.one_time_cents is None or item.one_time_cents == 0) and (
            item.recurring_cents is None or item.recurring_cents == 0
        ) and not item.incremental:
            warnings.append(
                f"{context}: fee item does not specify a one-time or recurring amount"
            )

        if item.one_time_cents is not None and item.one_time_cents < 0:
            errors.append(f"{context}: one_time_cents must be non-negative")

        if item.recurring_cents is not None and item.recurring_cents < 0:
            errors.append(f"{context}: recurring_cents must be non-negative")

        if item.recurring_cents and not item.recurring_interval:
            errors.append(f"{context}: missing recurring_interval for recurring_cents")

        if item.recurring_interval and not item.recurring_cents:
            errors.append(f"{context}: missing recurring_cents for recurring_interval")

        if item.recurring_interval and item.recurring_interval not in FeeItem._ANNUALIZATION_FACTORS:
            errors.append(
                f"{context}: unsupported recurring_interval '{item.recurring_interval}'"
            )

    return FeeValidationResult(is_valid=not errors, errors=errors, warnings=warnings)


def _coerce_iterable(items: FeeSchedule | Iterable[FeeItem]) -> Iterable[FeeItem]:
    if isinstance(items, FeeSchedule):
        return items.items
    return items


def total_one_time_cents(items: FeeSchedule | Iterable[FeeItem]) -> int:
    """Compute the total of one-time fees (in cents)."""

    return sum(item.one_time_cents or 0 for item in _coerce_iterable(items))


def total_recurring_annualized_cents(items: FeeSchedule | Iterable[FeeItem]) -> int:
    """Compute the total recurring fees normalized to an annual amount."""

    return sum(item.annualized_recurring_cents() for item in _coerce_iterable(items))


def has_incremental(items: FeeSchedule | Iterable[FeeItem]) -> bool:
    """Return True if any fee item is marked as incremental."""

    return any(item.incremental for item in _coerce_iterable(items))


__all__ = [
    "FeeItem",
    "FeeSchedule",
    "FeeValidationResult",
    "validate_fee_schedule",
    "total_one_time_cents",
    "total_recurring_annualized_cents",
    "has_incremental",
]
