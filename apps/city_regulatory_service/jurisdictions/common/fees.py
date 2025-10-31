"""Fee schedule models shared across jurisdiction ingest modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class FeeItem:
    """Single fee entry within a jurisdiction's schedule."""

    name: str
    amount_cents: int
    kind: str = "one_time"
    cadence: str | None = None
    unit: str | None = None
    incremental: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:  # pragma: no cover - trivial validation
        if self.amount_cents < 0:
            raise ValueError("Fee amounts must be non-negative")
        if not self.name:
            raise ValueError("Fee name must be provided")

    @property
    def is_recurring(self) -> bool:
        return self.kind.lower() == "recurring"

    def dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "amount_cents": self.amount_cents,
            "kind": self.kind,
            "cadence": self.cadence,
            "unit": self.unit,
            "incremental": self.incremental,
            "notes": self.notes,
        }
        return {key: value for key, value in payload.items() if value is not None}


def _annual_multiplier(cadence: str | None) -> int:
    cadence_normalized = (cadence or "annual").lower()
    return {
        "annual": 1,
        "yearly": 1,
        "monthly": 12,
        "quarterly": 4,
        "biannual": 2,
        "semiannual": 2,
        "weekly": 52,
        "daily": 365,
    }.get(cadence_normalized, 1)


@dataclass(frozen=True)
class FeeSchedule:
    """Collection of fee items for a jurisdiction."""

    jurisdiction: str
    paperwork: Sequence[str] = field(default_factory=tuple)
    fees: Sequence[FeeItem] = field(default_factory=tuple)

    def __post_init__(self) -> None:  # pragma: no cover - trivial validation
        if isinstance(self.paperwork, Iterable) and not isinstance(self.paperwork, (list, tuple)):
            object.__setattr__(self, "paperwork", tuple(self.paperwork))
        if isinstance(self.fees, Iterable) and not isinstance(self.fees, (list, tuple)):
            object.__setattr__(self, "fees", tuple(self.fees))

    @property
    def total_one_time_cents(self) -> int:
        return sum(item.amount_cents for item in self.fees if not item.is_recurring)

    @property
    def total_recurring_annualized_cents(self) -> int:
        return sum(
            item.amount_cents * _annual_multiplier(item.cadence)
            for item in self.fees
            if item.is_recurring
        )


@dataclass(frozen=True)
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

    paperwork_duplicates = {doc.lower() for doc in schedule.paperwork}
    if len(paperwork_duplicates) != len(tuple(schedule.paperwork)):
        issues.append("Duplicate paperwork entries detected")

    incremental_count = sum(1 for item in schedule.fees if item.incremental)
    return FeeValidationResult(
        is_valid=not issues,
        issues=issues,
        incremental_fee_count=incremental_count,
    )
