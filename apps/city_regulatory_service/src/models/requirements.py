"""Canonical requirement and fee data structures used by the estimator."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

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
    return FeeValidationResult(
        is_valid=not issues, issues=issues, incremental_fee_count=incremental_count
    )


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

"""Canonical requirement and fee models for cost estimation.

These models provide a unified representation of requirement bundles that can
be consumed by the cost estimator, API endpoints, and batch jobs.  They focus on
fee semantics (one-time vs recurring vs incremental) rather than the legacy
scraper-specific dataclasses that live under ``jurisdictions/common``.
"""

from collections.abc import Iterator
from typing import Any, ClassVar, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

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
    """Represents an individual fee that may be part of a requirement."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    requirement_id: str | None = Field(
        None, description="Identifier for the requirement that owns this fee"
    )
    label: str = Field(
        ...,
        description="Human readable label for the fee",
        validation_alias=AliasChoices("label", "name"),
        serialization_alias="label",
    )
    notes: str | None = Field(None, description="Additional context for the fee")
    one_time_cents: int | None = Field(
        None,
        ge=0,
        description="One-time amount for the fee in cents",
    )
    recurring_cents: int | None = Field(
        None,
        ge=0,
        description="Recurring amount for the fee in cents",
    )
    recurring_interval: RecurringInterval | None = Field(
        None,
        description="Interval describing how frequently the recurring amount is charged",
    )
    incremental: bool = Field(
        False,
        description="Whether the fee scales with quantity (per application, inspection, etc.)",
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

    def annualized_recurring_cents(self) -> int:
        """Return the recurring amount normalized to an annual basis."""

        if not self.recurring_cents or not self.recurring_interval:
            return 0
        factor = self._ANNUALIZATION_FACTORS.get(self.recurring_interval, 0)
        return int(self.recurring_cents * factor)

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:  # pragma: no cover - thin wrapper
        """Compatibility wrapper for callers that still expect ``dict()``."""

        if not args and not kwargs:
            return self.model_dump(by_alias=True, exclude_none=True)
        return self.model_dump(*args, **kwargs)


class FeeSchedule(BaseModel):
    """Collection of fee items associated with a jurisdiction or requirement."""

    model_config = ConfigDict(populate_by_name=True)

    jurisdiction_id: str | None = Field(
        None, description="Identifier of the jurisdiction the schedule belongs to"
    )
    jurisdiction_name: str | None = Field(None, description="Display name of the jurisdiction")
    state: str | None = Field(None, description="State/region for the jurisdiction")
    paperwork: list[str] = Field(default_factory=list, description="Paperwork checklist")
    items: list[FeeItem] = Field(
        default_factory=list,
        description="Fee items that make up the schedule",
        validation_alias=AliasChoices("items", "fees"),
        serialization_alias="items",
    )

    @property
    def fees(self) -> list[FeeItem]:  # pragma: no cover - simple proxy
        """Compatibility alias used by legacy ingestors."""

        return self.items

    def iter_items(self) -> Iterator[FeeItem]:
        """Iterate through fee items."""

        yield from self.items

    @property
    def total_one_time_cents(self) -> int:
        """Total one-time fees in cents."""

        return sum(item.one_time_cents or 0 for item in self.items)

    @property
    def total_recurring_annualized_cents(self) -> int:
        """Total recurring fees annualized to a yearly amount in cents."""

        return sum(item.annualized_recurring_cents() for item in self.items)

    @property
    def has_incremental(self) -> bool:
        """Whether any fee item is marked as incremental."""

        return any(item.incremental for item in self.items)

    def extend(self, other: Iterable[FeeItem] | FeeSchedule) -> None:
        """Append items from another schedule or iterable."""

        if isinstance(other, FeeSchedule):
            self.items.extend(other.items)
        else:
            self.items.extend(other)


class RequirementsBundle(BaseModel):
    """Bundle of requirements and their associated fee schedules for a jurisdiction."""

    class Requirement(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        requirement_id: str = Field(..., description="Normalized requirement identifier")
        label: str = Field(..., description="Display name for the requirement")
        agency: str | None = Field(None, description="Agency responsible for the requirement")
        fee_schedule: FeeSchedule = Field(
            default_factory=FeeSchedule,
            description="Fee schedule specific to the requirement",
        )
        metadata: dict[str, Any] = Field(
            default_factory=dict,
            description="Additional context useful for reporting",
        )

        @property
        def total_one_time_cents(self) -> int:  # pragma: no cover - simple proxy
            return self.fee_schedule.total_one_time_cents

        @property
        def total_recurring_annualized_cents(self) -> int:  # pragma: no cover - simple proxy
            return self.fee_schedule.total_recurring_annualized_cents

        @property
        def has_incremental(self) -> bool:  # pragma: no cover - simple proxy
            return self.fee_schedule.has_incremental

    model_config = ConfigDict(populate_by_name=True)

    jurisdiction_id: str = Field(..., description="Identifier of the jurisdiction")
    jurisdiction_name: str = Field(..., description="Display name of the jurisdiction")
    state: str = Field(..., description="State/region for the jurisdiction")
    requirements: list[Requirement] = Field(
        default_factory=list,
        description="Requirement entries included in the bundle",
    )

    def iter_fee_items(self) -> Iterator[FeeItem]:
        """Iterate through all fee items in the bundle."""

        for requirement in self.requirements:
            yield from requirement.fee_schedule.iter_items()

    @property
    def fee_schedule(self) -> FeeSchedule:
        """Aggregate fee schedule across every requirement in the bundle."""

        schedule = FeeSchedule(
            jurisdiction_id=self.jurisdiction_id,
            jurisdiction_name=self.jurisdiction_name,
            state=self.state,
        )
        schedule.extend(self.iter_fee_items())
        return schedule


__all__ = ["FeeItem", "FeeSchedule", "RequirementsBundle"]
