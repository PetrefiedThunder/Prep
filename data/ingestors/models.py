"""Shared dataclasses and validation helpers for fee schedule ingestors."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date


@dataclass(slots=True, frozen=True)
class FeeComponent:
    """Single line item within a jurisdictional fee schedule."""

    name: str
    amount: float | None
    cadence: str
    description: str | None = None


@dataclass(slots=True, frozen=True)
class FeeSchedule:
    """Structured representation of a municipal fee schedule."""

    jurisdiction: str
    program: str
    agency: str
    renewal_frequency: str
    components: tuple[FeeComponent, ...]
    currency: str = "USD"
    payment_methods: tuple[str, ...] = ()
    effective_date: date | None = None
    notes: str | None = None
    references: tuple[str, ...] = ()

    def component_count(self) -> int:
        """Return the number of components included in the schedule."""

        return len(self.components)


def _validate_currency(code: str) -> None:
    if len(code) != 3 or not code.isalpha() or code.upper() != code:
        raise ValueError(f"Currency codes must be 3 upper-case letters, got '{code}'.")


def _validate_components(components: Iterable[FeeComponent]) -> tuple[FeeComponent, ...]:
    validated: list[FeeComponent] = []
    for component in components:
        if not isinstance(component, FeeComponent):
            raise TypeError("Components must be instances of FeeComponent.")
        if not component.name.strip():
            raise ValueError("Fee component names cannot be empty.")
        if component.amount is not None and component.amount < 0:
            raise ValueError(f"Fee amounts must be non-negative, got {component.amount!r}.")
        if not component.cadence.strip():
            raise ValueError("Fee component cadence cannot be empty.")
        validated.append(component)
    if not validated:
        raise ValueError("Fee schedules must include at least one component.")
    return tuple(validated)


def validate_fee_schedule(schedule: FeeSchedule) -> FeeSchedule:
    """Validate *schedule* ensuring the basic invariants hold."""

    if not isinstance(schedule, FeeSchedule):
        raise TypeError("validate_fee_schedule expects a FeeSchedule instance.")

    if not schedule.jurisdiction.strip():
        raise ValueError("Jurisdiction cannot be empty.")
    if not schedule.program.strip():
        raise ValueError("Program name cannot be empty.")
    if not schedule.agency.strip():
        raise ValueError("Agency cannot be empty.")
    if not schedule.renewal_frequency.strip():
        raise ValueError("Renewal frequency cannot be empty.")

    _validate_currency(schedule.currency)

    validated_components = _validate_components(schedule.components)

    for method in schedule.payment_methods:
        if not method.strip():
            raise ValueError("Payment method entries cannot be empty strings.")

    if schedule.references:
        for reference in schedule.references:
            if not reference.strip():
                raise ValueError("Reference URLs cannot be empty strings.")

    return FeeSchedule(
        jurisdiction=schedule.jurisdiction.strip(),
        program=schedule.program.strip(),
        agency=schedule.agency.strip(),
        renewal_frequency=schedule.renewal_frequency.strip(),
        components=validated_components,
        currency=schedule.currency.upper(),
        payment_methods=tuple(method.strip() for method in schedule.payment_methods),
        effective_date=schedule.effective_date,
        notes=schedule.notes.strip() if schedule.notes else None,
        references=tuple(reference.strip() for reference in schedule.references),
    )


__all__ = ["FeeComponent", "FeeSchedule", "validate_fee_schedule"]
