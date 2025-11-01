"""City Regulatory Service source modules."""

from .estimator import CostEstimate, RequirementCostBreakdown, estimate_costs, load_bundle

try:  # pragma: no cover - gracefully degrade if regulatory models unavailable
    from .models import (
        CityAgency,
        CityComplianceTemplate,
        CityETLRun,
        CityJurisdiction,
        CityRequirement,
        CityRequirementLink,
        FeeItem,
        FeeSchedule,
        FeeValidationResult,
        Jurisdiction,
        RequirementRecord,
        RequirementsBundle,
        has_incremental,
        make_fee_schedule,
        total_one_time_cents,
        total_recurring_annualized_cents,
        validate_fee_schedule,
    )
except Exception:  # pragma: no cover - exposed attributes set to None for tests
    CityAgency = CityComplianceTemplate = CityETLRun = None
    CityJurisdiction = CityRequirement = CityRequirementLink = None
    FeeItem = FeeSchedule = FeeValidationResult = None
    Jurisdiction = RequirementRecord = RequirementsBundle = None
    make_fee_schedule = validate_fee_schedule = None
    total_one_time_cents = total_recurring_annualized_cents = None
    has_incremental = None

__all__ = [
    "CostEstimate",
    "RequirementCostBreakdown",
    "estimate_costs",
    "load_bundle",
    "CityJurisdiction",
    "CityAgency",
    "CityRequirement",
    "CityRequirementLink",
    "CityComplianceTemplate",
    "CityETLRun",
    "FeeItem",
    "FeeSchedule",
    "FeeValidationResult",
    "Jurisdiction",
    "RequirementRecord",
    "RequirementsBundle",
    "make_fee_schedule",
    "validate_fee_schedule",
    "total_one_time_cents",
    "total_recurring_annualized_cents",
    "has_incremental",
]
