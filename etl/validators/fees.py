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
