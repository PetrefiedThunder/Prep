"""Shared fee schedule models for city regulatory ingestors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


_VALID_KINDS = {"one_time", "recurring", "incremental"}
_ANNUALIZED_CADENCE = {
    "annual": 1,
    "yearly": 1,
    "semi_annual": 2,
    "biannual": 2,
    "quarterly": 4,
    "monthly": 12,
}


@dataclass(frozen=True, slots=True)
class FeeItem:
    """Single fee entry within a jurisdiction's schedule."""

    name: str
    amount_cents: int
    kind: str = "one_time"
    cadence: str | None = None
    unit: str | None = None
    incremental: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:  # pragma: no cover - simple validation
        if not self.name:
            raise ValueError("Fee name must be provided")
        if self.amount_cents < 0:
            raise ValueError("Fee amounts must be non-negative")
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"Unsupported fee kind '{self.kind}'")

    @property
    def is_recurring(self) -> bool:
        return self.kind == "recurring"

    def annualized_amount_cents(self) -> int:
        if not self.is_recurring:
            return 0
        cadence = (self.cadence or "annual").lower()
        multiplier = _ANNUALIZED_CADENCE.get(cadence, 1)
        return self.amount_cents * multiplier

    def dict(self) -> dict[str, object]:
        payload = {
            "name": self.name,
            "amount_cents": self.amount_cents,
            "kind": self.kind,
            "cadence": self.cadence,
            "unit": self.unit,
            "incremental": self.incremental,
            "notes": self.notes,
        }
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    """Collection of fee items for a jurisdiction."""

    jurisdiction: str
    paperwork: Sequence[str] = field(default_factory=tuple)
    fees: Sequence[FeeItem] = field(default_factory=tuple)

    def __post_init__(self) -> None:  # pragma: no cover - structural normalization
        if isinstance(self.paperwork, Iterable) and not isinstance(self.paperwork, tuple):
            object.__setattr__(self, "paperwork", tuple(self.paperwork))
        if isinstance(self.fees, Iterable) and not isinstance(self.fees, tuple):
            object.__setattr__(self, "fees", tuple(self.fees))

    @property
    def total_one_time_cents(self) -> int:
        return sum(item.amount_cents for item in self.fees if not item.is_recurring)

    @property
    def total_recurring_annualized_cents(self) -> int:
        return sum(item.annualized_amount_cents() for item in self.fees)


@dataclass(frozen=True, slots=True)
class FeeValidationResult:
    """Validation payload summarizing potential issues."""

    is_valid: bool
    issues: list[str]
    incremental_fee_count: int


def validate_fee_schedule(schedule: FeeSchedule) -> FeeValidationResult:
    """Validate that a fee schedule is internally consistent."""

    issues: list[str] = []

    seen_names: set[str] = set()
    for item in schedule.fees:
        key = item.name.lower()
        if key in seen_names:
            issues.append(f"Duplicate fee entry detected: {item.name}")
        else:
            seen_names.add(key)
        if item.amount_cents < 0:
            issues.append(f"Negative amount for fee: {item.name}")

    paperwork_lower = [doc.lower() for doc in schedule.paperwork]
    if len(set(paperwork_lower)) != len(schedule.paperwork):
        issues.append("Duplicate paperwork entries detected")

    incremental_count = sum(1 for item in schedule.fees if item.incremental)
    return FeeValidationResult(
        is_valid=not issues,
        issues=issues,
        incremental_fee_count=incremental_count,
    )


__all__ = ["FeeItem", "FeeSchedule", "FeeValidationResult", "validate_fee_schedule"]

