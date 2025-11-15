"""Fee schedule validation helpers used by ETL pipelines."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

_VALID_KINDS: set[str] = {"one_time", "recurring", "incremental"}
_VALID_CADENCE: dict[str, int] = {
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
_INCREMENTAL_UNITS: set[str] = {
    "per_permit",
    "per_inspection",
    "per_application",
    "per_reinspection",
}


def _coerce(items: Iterable[object]) -> list[object]:
    return list(items)


def _get_attr(item: object, name: str) -> object:
    if isinstance(item, Mapping):
        return item.get(name)  # type: ignore[return-value]
    return getattr(item, name, None)


def _iter_fees(schedule: object) -> Sequence[object]:
    if isinstance(schedule, Mapping):
        fees = schedule.get("fees") or schedule.get("items")
        if isinstance(fees, Iterable):
            return _coerce(fees)
        raise FeeValidationError(["Fee schedule payload missing 'fees' collection"])
    fees = getattr(schedule, "fees", None)
    if fees is None:
        raise FeeValidationError(["Fee schedule object missing 'fees' attribute"])
    return _coerce(fees)


def _total_from_schedule(schedule: object, attr: str) -> int | None:
    value = getattr(schedule, attr, None)
    if isinstance(value, int):
        return value
    if isinstance(schedule, Mapping):
        totals = schedule.get("totals")
        if isinstance(totals, Mapping):
            total_value = totals.get(attr)
            if isinstance(total_value, (int, float)):
                return int(total_value)
    return None


@dataclass(slots=True)
class FeeValidationSummary:
    """Normalized view of the fee validation results."""

    issues: list[str]
    counts_by_kind: dict[str, int]
    totals: dict[str, int]


class FeeValidationError(ValueError):
    """Raised when a fee schedule fails validation checks."""

    def __init__(self, issues: Sequence[str]) -> None:
        joined = "\n - ".join(issues)
        message = (
            f"Fee schedule validation failed:\n - {joined}" if issues else "Invalid fee schedule"
        )
        super().__init__(message)
        self.issues = list(issues)


def validate_fee_schedule(schedule: object, *, raise_on_error: bool = True) -> FeeValidationSummary:
    """Validate a fee schedule object or mapping.

    The validator ensures that fee kinds, cadence values, and incremental units
    are coherent and that the provided totals reconcile with the individual fee
    items.  When ``raise_on_error`` is ``True`` (the default) a
    :class:`FeeValidationError` is raised if any issues are discovered.
    """

    issues: list[str] = []
    counts: dict[str, int] = dict.fromkeys(_VALID_KINDS, 0)
    fees = _iter_fees(schedule)
    if not fees:
        issues.append("Fee schedule must include at least one fee item")

    total_one_time = 0
    total_recurring = 0
    incremental_count = 0

    for index, fee in enumerate(fees, start=1):
        name = str(_get_attr(fee, "name") or f"fee #{index}")
        kind = str(_get_attr(fee, "kind") or "").lower()
        if kind not in _VALID_KINDS:
            issues.append(f"Fee '{name}' has unsupported kind '{kind or '<missing>'}'")
            continue

        counts[kind] += 1

        amount = _get_attr(fee, "amount_cents")
        if not isinstance(amount, int) or amount < 0:
            issues.append(f"Fee '{name}' must have a non-negative integer amount_cents")

        cadence = _get_attr(fee, "cadence")
        cadence_str = None if cadence in (None, "") else str(cadence).lower()

        if kind == "recurring":
            if not cadence_str:
                issues.append(f"Recurring fee '{name}' must provide a cadence")
            elif cadence_str not in _VALID_CADENCE:
                issues.append(f"Recurring fee '{name}' uses unsupported cadence '{cadence_str}'")
            if isinstance(amount, int) and amount >= 0 and cadence_str in _VALID_CADENCE:
                total_recurring += amount * _VALID_CADENCE[cadence_str]

        if kind == "one_time" and isinstance(amount, int) and amount >= 0:
            total_one_time += amount

        unit = _get_attr(fee, "unit")
        unit_str = str(unit).lower() if isinstance(unit, str) else None

        is_incremental = bool(_get_attr(fee, "incremental")) or kind == "incremental"
        if is_incremental:
            incremental_count += 1
            if not unit_str:
                issues.append(f"Incremental fee '{name}' must specify a unit")
            elif unit_str not in _INCREMENTAL_UNITS:
                issues.append(f"Incremental fee '{name}' has unsupported unit '{unit_str}'")
        elif unit_str and unit_str not in _INCREMENTAL_UNITS:
            issues.append(f"Fee '{name}' provides unit '{unit_str}' but is not marked incremental")

    provided_one_time = _total_from_schedule(schedule, "one_time_cents")
    if provided_one_time is not None and provided_one_time != total_one_time:
        issues.append(
            "one_time_cents total does not match summed fee amounts"
            f" (expected {total_one_time}, found {provided_one_time})"
        )

    provided_recurring = _total_from_schedule(schedule, "recurring_annualized_cents")
    if provided_recurring is not None and provided_recurring != total_recurring:
        issues.append(
            "recurring_annualized_cents total does not match annualised fees"
            f" (expected {total_recurring}, found {provided_recurring})"
        )

    provided_incremental = _total_from_schedule(schedule, "incremental_fee_count")
    if provided_incremental is not None and provided_incremental != incremental_count:
        issues.append(
            "incremental_fee_count does not match number of incremental fees"
            f" (expected {incremental_count}, found {provided_incremental})"
        )

    summary = FeeValidationSummary(
        issues=list(issues),
        counts_by_kind=counts,
        totals={
            "one_time_cents": total_one_time,
            "recurring_annualized_cents": total_recurring,
            "incremental_fee_count": incremental_count,
        },
    )

    if issues and raise_on_error:
        raise FeeValidationError(issues)

    return summary
