"""Canonical requirement and fee data structures used by the estimator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Mapping, Sequence

_CADENCE_ALIASES: Mapping[str, str] = {
    "annual": "annual",
    "annually": "annual",
    "per_year": "annual",
    "per_annum": "annual",
    "yearly": "annual",
    "semiannual": "semi_annual",
    "semi-annual": "semi_annual",
    "semi_annual": "semi_annual",
    "biannual": "semi_annual",
    "biennial": "biennial",
    "quarterly": "quarterly",
    "per_quarter": "quarterly",
    "monthly": "monthly",
    "per_month": "monthly",
    "weekly": "weekly",
    "per_week": "weekly",
    "daily": "daily",
    "per_day": "daily",
}

_CADENCE_FACTORS: Mapping[str, float] = {
    "annual": 1.0,
    "biennial": 0.5,
    "semi_annual": 2.0,
    "quarterly": 4.0,
    "monthly": 12.0,
    "weekly": 52.0,
    "daily": 365.0,
}


def _normalize_cadence(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return _CADENCE_ALIASES.get(normalized, normalized)


@dataclass(slots=True)
class FeeItem:
    """Represents a single fee entry in a jurisdiction's schedule."""

    name: str
    amount_cents: int
    kind: str = "one_time"
    cadence: str | None = None
    unit: str | None = None
    incremental: bool = False
    notes: str | None = None
    requirement_id: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Fee name must be provided")
        if self.amount_cents < 0:
            raise ValueError("Fee amounts must be non-negative")

        normalized_kind = self.kind.lower()
        if normalized_kind not in {"one_time", "recurring", "incremental"}:
            raise ValueError(f"Unsupported fee kind '{self.kind}'")
        self.kind = normalized_kind

        cadence = _normalize_cadence(self.cadence)
        if cadence and cadence not in _CADENCE_FACTORS:
            raise ValueError(f"Unsupported cadence '{self.cadence}'")
        self.cadence = cadence

        if self.kind == "recurring" and not cadence and not self.incremental:
            raise ValueError("Recurring fees must provide a cadence")

        if self.kind == "incremental":
            self.incremental = True

    @property
    def is_recurring(self) -> bool:
        return self.kind == "recurring" and not self.incremental

    def annualized_amount_cents(self) -> int:
        if not self.is_recurring or not self.cadence:
            return 0
        factor = _CADENCE_FACTORS.get(self.cadence, 0.0)
        return int(round(self.amount_cents * factor))

    def dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": self.name,
            "amount_cents": self.amount_cents,
            "kind": self.kind,
            "cadence": self.cadence,
            "unit": self.unit,
            "incremental": self.incremental,
            "notes": self.notes,
            "requirement_id": self.requirement_id,
        }
        return {key: value for key, value in payload.items() if value not in {None, ""}}


@dataclass(slots=True)
class FeeSchedule:
    """Collection of fee items along with supporting paperwork."""

    jurisdiction: str
    paperwork: Sequence[str] = field(default_factory=tuple)
    fees: Sequence[FeeItem] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        paperwork_tuple = tuple(dict.fromkeys(item for item in self.paperwork))
        fees_tuple = tuple(self.fees)
        object.__setattr__(self, "paperwork", paperwork_tuple)
        object.__setattr__(self, "fees", fees_tuple)

    @property
    def total_one_time_cents(self) -> int:
        return sum(item.amount_cents for item in self.fees if item.kind == "one_time")

    @property
    def total_recurring_annualized_cents(self) -> int:
        return sum(item.annualized_amount_cents() for item in self.fees)

    @property
    def incremental_fee_count(self) -> int:
        return sum(1 for item in self.fees if item.incremental)


@dataclass(slots=True)
class FeeValidationResult:
    """Validation payload summarizing potential issues."""

    is_valid: bool
    issues: list[str]
    incremental_fee_count: int


def validate_fee_schedule(schedule: FeeSchedule) -> FeeValidationResult:
    issues: list[str] = []
    seen: set[str] = set()

    for fee in schedule.fees:
        key = fee.name.strip().lower()
        if key in seen:
            issues.append(f"Duplicate fee item detected: {fee.name}")
        else:
            seen.add(key)

        if fee.kind == "recurring" and not fee.cadence:
            issues.append(f"Recurring fee '{fee.name}' missing cadence")

    incremental_count = schedule.incremental_fee_count
    return FeeValidationResult(is_valid=not issues, issues=issues, incremental_fee_count=incremental_count)


def make_fee_schedule(
    jurisdiction: str,
    *,
    paperwork: Iterable[str] | None = None,
    fees: Iterable[FeeItem] | None = None,
) -> FeeSchedule:
    return FeeSchedule(
        jurisdiction=jurisdiction,
        paperwork=tuple(paperwork or ()),
        fees=tuple(fees or ()),
    )


def total_one_time_cents(items: FeeSchedule | Iterable[FeeItem]) -> int:
    iterable = items.fees if isinstance(items, FeeSchedule) else items
    return sum(item.amount_cents for item in iterable if item.kind == "one_time")


def total_recurring_annualized_cents(items: FeeSchedule | Iterable[FeeItem]) -> int:
    iterable = items.fees if isinstance(items, FeeSchedule) else items
    return sum(item.annualized_amount_cents() for item in iterable)


def has_incremental(items: FeeSchedule | Iterable[FeeItem]) -> bool:
    iterable = items.fees if isinstance(items, FeeSchedule) else items
    return any(item.incremental for item in iterable)


@dataclass(slots=True, frozen=True)
class Jurisdiction:
    """Lightweight jurisdiction metadata used in requirement bundles."""

    id: str
    city: str
    state: str
    county: str | None = None
    country_code: str = "US"


@dataclass(slots=True, frozen=True)
class RequirementRecord:
    """Normalized requirement data used by the estimator."""

    id: str
    label: str
    requirement_type: str
    applies_to: tuple[str, ...]
    required_documents: tuple[str, ...]
    submission_channel: str | None
    application_url: str | None
    inspection_required: bool
    renewal_frequency: str | None
    fee_schedule: str | None
    fee_amount_cents: int | None
    agency_name: str | None
    agency_type: str | None
    source_url: str | None


@dataclass(slots=True)
class RequirementsBundle:
    """Complete view of requirements and fees for a jurisdiction."""

    jurisdiction: Jurisdiction
    requirements: tuple[RequirementRecord, ...]
    fee_schedule: FeeSchedule
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def paperwork(self) -> tuple[str, ...]:
        return self.fee_schedule.paperwork


__all__ = [
    "FeeItem",
    "FeeSchedule",
    "FeeValidationResult",
    "Jurisdiction",
    "RequirementRecord",
    "RequirementsBundle",
    "validate_fee_schedule",
    "make_fee_schedule",
    "total_one_time_cents",
    "total_recurring_annualized_cents",
    "has_incremental",
]

