"""Database and domain models for the city regulatory service."""

# Import SQLAlchemy models from the shared regulatory package
try:  # pragma: no cover - degrade gracefully when dependencies unavailable
    from prep.regulatory.models import (
        CityAgency,
        CityComplianceTemplate,
        CityETLRun,
        CityJurisdiction,
        CityRequirement,
        CityRequirementLink,
    )
except Exception:  # pragma: no cover - set placeholders for test environments
    CityAgency = CityComplianceTemplate = CityETLRun = None
    CityJurisdiction = CityRequirement = CityRequirementLink = None

# Canonical dataclasses used by the estimator and ingestors
from .requirements import (
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
# Import ORM entities from the shared regulatory module
from prep.regulatory.models import (
    CityAgency,
    CityComplianceTemplate,
    CityFeeSchedule,
    CityETLRun,
    CityJurisdiction,
    CityRequirement,
    CityRequirementLink,
)

# Domain-level models that power estimators and API responses
from .requirements import FeeItem, FeeSchedule, RequirementsBundle

__all__ = [
    "CityJurisdiction",
    "CityAgency",
    "CityRequirement",
    "CityFeeSchedule",
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
    "RequirementsBundle",
]
