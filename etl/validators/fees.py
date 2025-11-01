"""Fee schedule validation helpers used by ETL pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

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
        message = f"Fee schedule validation failed:\n - {joined}" if issues else "Invalid fee schedule"
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
    counts: dict[str, int] = {kind: 0 for kind in _VALID_KINDS}
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
        if cadence in (None, ""):
            cadence_str = None
        else:
            cadence_str = str(cadence).lower()

        if kind == "recurring":
            if not cadence_str:
                issues.append(f"Recurring fee '{name}' must provide a cadence")
            elif cadence_str not in _VALID_CADENCE:
                issues.append(
                    f"Recurring fee '{name}' uses unsupported cadence '{cadence_str}'"
                )
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
            issues.append(
                f"Fee '{name}' provides unit '{unit_str}' but is not marked incremental"
            )

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
from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import sys, json

FeeKind = Literal["one_time", "recurring", "incremental"]
class FeeItem(BaseModel):
    name: str
    amount_cents: int = Field(ge=0)
    kind: FeeKind
    cadence: Optional[Literal["annual","semi_annual","quarterly","monthly","per_permit","per_inspection","per_application"]] = None
    unit: Optional[str] = None
    tier_min_inclusive: Optional[int] = None
    tier_max_inclusive: Optional[int] = None
class FeeSchedule(BaseModel):
    jurisdiction: str
    paperwork: List[str] = Field(default_factory=list)
    fees: List[FeeItem] = Field(default_factory=list)
    @property
    def total_one_time_cents(self) -> int:
        return sum(f.amount_cents for f in self.fees if f.kind == "one_time")
    @property
    def total_recurring_annualized_cents(self) -> int:
        factor = {None: 1.0, "annual": 1.0, "semi_annual": 2.0, "quarterly": 4.0, "monthly": 12.0, "per_permit": 1.0, "per_application": 1.0}
        return sum(int(f.amount_cents * factor.get(f.cadence, 1.0)) for f in self.fees if f.kind == "recurring")
class FeeValidationResult(BaseModel):
    is_valid: bool
    issues: List[str]
    total_one_time_cents: int
    total_recurring_annualized_cents: int
    incremental_fee_count: int
def validate_fee_schedule(schedule: FeeSchedule) -> FeeValidationResult:
    issues: List[str] = []
    if not schedule.fees: issues.append("No fees present.")
    if not schedule.paperwork: issues.append("No paperwork/forms listed.")
    for f in schedule.fees:
        if f.amount_cents < 0: issues.append(f"Negative amount for {f.name}")
        if f.kind == "recurring" and f.cadence is None: issues.append(f"Recurring fee missing cadence: {f.name}")
        if f.kind == "incremental" and (f.unit is None): issues.append(f"Incremental fee missing unit: {f.name}")
        if f.kind == "incremental":
            lo, hi = f.tier_min_inclusive, f.tier_max_inclusive
            if lo is not None and hi is not None and lo > hi: issues.append(f"Invalid tier range in {f.name}")
    one_time = schedule.total_one_time_cents
    recurring = schedule.total_recurring_annualized_cents
    incr_count = sum(1 for f in schedule.fees if f.kind == "incremental")
    if schedule.paperwork and (one_time + recurring == 0) and incr_count == 0:
        issues.append("Paperwork exists but no monetary signal.")
    return FeeValidationResult(is_valid=(len(issues) == 0), issues=issues,
                               total_one_time_cents=one_time,
                               total_recurring_annualized_cents=recurring,
                               incremental_fee_count=incr_count)
if __name__ == "__main__":
    data = json.load(sys.stdin) if not sys.stdin.isatty() else {
        "jurisdiction": "san_francisco",
        "paperwork": ["Application Form A-FOOD"],
        "fees": [
            {"name":"Plan Review","amount_cents":45000,"kind":"one_time"},
            {"name":"Annual Permit","amount_cents":98000,"kind":"recurring","cadence":"annual"}
        ]
    }
    res = validate_fee_schedule(FeeSchedule(**data))
    print(res.model_dump_json(indent=2))
    sys.exit(0 if res.is_valid else 1)
