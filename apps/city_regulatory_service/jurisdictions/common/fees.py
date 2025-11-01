"""Common fee schedule primitives used by city ingestors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence
"""Compatibility exports for jurisdiction fee schedules."""

from __future__ import annotations

from apps.city_regulatory_service.src.models.requirements import (
    FeeItem,
    FeeSchedule,
    FeeValidationResult,
    RequirementsBundle,
    has_incremental,
    make_fee_schedule,
    total_one_time_cents,
    total_recurring_annualized_cents,
    validate_fee_schedule,
)

__all__ = [
    "FeeItem",
    "FeeSchedule",
    "FeeValidationResult",
    "has_incremental",
    "total_one_time_cents",
    "total_recurring_annualized_cents",
    "make_fee_schedule",
    "validate_fee_schedule",
]

_VALID_KINDS = {"one_time", "recurring", "incremental"}
_ANNUAL_MULTIPLIER = {
    "annual": 1,
    "yearly": 1,
    "semi_annual": 2,
    "semiannual": 2,
    "biannual": 2,
    "quarterly": 4,
    "monthly": 12,
    "weekly": 52,
    "daily": 365,
}
_INCREMENTAL_UNITS = {
    "per_permit",
    "per_inspection",
    "per_application",
    "per_reinspection",
}


@dataclass(slots=True, frozen=True)
class FeeItem:
    """Single fee entry within a jurisdiction's schedule."""

    name: str
    amount_cents: int
    kind: str = "one_time"
    cadence: str | None = None
    unit: str | None = None
    incremental: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("fee name must be provided")
        if self.amount_cents < 0:
            raise ValueError("fee amount must be non-negative")
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"unsupported fee kind '{self.kind}'")
        if self.kind == "recurring":
            cadence = (self.cadence or "annual").lower()
            object.__setattr__(self, "cadence", cadence)
        if self.kind == "incremental" and self.unit:
            if self.unit not in _INCREMENTAL_UNITS:
                raise ValueError(f"unsupported incremental unit '{self.unit}'")

    @property
    def is_recurring(self) -> bool:
        return self.kind == "recurring"

    def annualized_amount_cents(self) -> int:
        if not self.is_recurring:
            return 0
        cadence = self.cadence or "annual"
        return self.amount_cents * _ANNUAL_MULTIPLIER.get(cadence, 1)

    def dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "amount_cents": self.amount_cents,
            "kind": self.kind,
            "cadence": self.cadence,
            "unit": self.unit,
            "incremental": self.incremental,
            "notes": self.notes,
        }


@dataclass(slots=True, frozen=True)
class FeeSchedule:
    """Collection of fee items for a jurisdiction."""

    jurisdiction: str
    paperwork: Sequence[str] = field(default_factory=tuple)
    fees: Sequence[FeeItem] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.jurisdiction:
            raise ValueError("jurisdiction identifier is required")
        paperwork: Iterable[str] = tuple(self.paperwork)
        fees: Iterable[FeeItem] = tuple(self.fees)
        object.__setattr__(self, "paperwork", paperwork)
        object.__setattr__(self, "fees", fees)

    @property
    def total_one_time_cents(self) -> int:
        return sum(item.amount_cents for item in self.fees if item.kind == "one_time")

    @property
    def total_recurring_annualized_cents(self) -> int:
        return sum(item.annualized_amount_cents() for item in self.fees if item.is_recurring)


@dataclass(slots=True, frozen=True)
class FeeValidationResult:
    """Validation payload summarising potential issues."""

    is_valid: bool
    issues: list[str]
    incremental_fee_count: int


def make_fee_schedule(
    jurisdiction: str,
    *,
    paperwork: Iterable[str] | None = None,
    fees: Iterable[FeeItem] | None = None,
) -> FeeSchedule:
    """Helper to construct a :class:`FeeSchedule` with sensible defaults."""

    return FeeSchedule(
        jurisdiction=jurisdiction,
        paperwork=tuple(paperwork or ()),
        fees=tuple(fees or ()),
    )


def validate_fee_schedule(schedule: FeeSchedule) -> FeeValidationResult:
    """Validate a fee schedule returning any detected issues."""

    issues: list[str] = []
    seen_names: set[str] = set()
    incremental_count = 0

    for idx, fee in enumerate(schedule.fees):
        key = fee.name.lower()
        if key in seen_names:
            issues.append(f"duplicate fee entry detected: {fee.name}")
        else:
            seen_names.add(key)

        if fee.kind == "recurring":
            cadence = fee.cadence or "annual"
            if cadence not in _ANNUAL_MULTIPLIER:
                issues.append(
                    f"recurring fee '{fee.name}' has unsupported cadence '{cadence}'"
                )
        if fee.kind == "incremental":
            incremental_count += 1
            if not fee.unit:
                issues.append(f"incremental fee '{fee.name}' is missing a unit")
        if fee.amount_cents < 0:
            issues.append(f"fee '{fee.name}' has a negative amount")
        if not fee.name:
            issues.append(f"fee #{idx + 1} is missing a name")

    paperwork = [doc.lower() for doc in schedule.paperwork]
    if len(paperwork) != len(set(paperwork)):
        issues.append("duplicate paperwork entries detected")

    return FeeValidationResult(
        is_valid=not issues,
        issues=issues,
        incremental_fee_count=incremental_count,
    )


def _iter_items(schedule_or_items: FeeSchedule | Iterable[FeeItem]) -> Iterable[FeeItem]:
    if isinstance(schedule_or_items, FeeSchedule):
        return schedule_or_items.fees
    return schedule_or_items


def total_one_time_cents(schedule_or_items: FeeSchedule | Iterable[FeeItem]) -> int:
    """Return the total one-time cost for the provided schedule or sequence."""

    return sum(item.amount_cents for item in _iter_items(schedule_or_items) if item.kind == "one_time")


def total_recurring_annualized_cents(schedule_or_items: FeeSchedule | Iterable[FeeItem]) -> int:
    """Return the annualised recurring cost for the provided schedule or sequence."""

    return sum(item.annualized_amount_cents() for item in _iter_items(schedule_or_items) if item.is_recurring)


def has_incremental(schedule_or_items: FeeSchedule | Iterable[FeeItem]) -> bool:
    """Return ``True`` if any incremental fees are present."""

    return any(item.kind == "incremental" for item in _iter_items(schedule_or_items))
    "RequirementsBundle",
    "validate_fee_schedule",
    "make_fee_schedule",
    "total_one_time_cents",
    "total_recurring_annualized_cents",
    "has_incremental",
]

