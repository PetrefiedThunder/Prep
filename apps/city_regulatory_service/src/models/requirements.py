"""Canonical requirement and fee models for cost estimation.

These models provide a unified representation of requirement bundles that can
be consumed by the cost estimator, API endpoints, and batch jobs.  They focus on
fee semantics (one-time vs recurring vs incremental) rather than the legacy
scraper-specific dataclasses that live under ``jurisdictions/common``.
"""

from __future__ import annotations

from typing import Any, ClassVar, Iterable, Iterator, Literal

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
    jurisdiction_name: str | None = Field(
        None, description="Display name of the jurisdiction"
    )
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

    def extend(self, other: Iterable[FeeItem] | "FeeSchedule") -> None:
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
        agency: str | None = Field(
            None, description="Agency responsible for the requirement"
        )
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
