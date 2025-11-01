"""Synthetic ingestion payloads for Joshua Tree, California."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.city_regulatory_service.models import FacilityType, RegulationType
from . import DATA_SOURCE, JURISDICTION_NAME, OPA_PACKAGE, STATE

JURISDICTION_INFO: Dict[str, Any] = {
    "county": "San Bernardino County",
    "country_code": "US",
    "fips_code": "06071",
    "population": 7414,
    "health_department_name": "San Bernardino County Environmental Health Services",
    "health_department_url": "https://dph.sbcounty.gov/programs/ehs/",
    "business_licensing_dept": "San Bernardino County Clerk of the Board",
    "business_licensing_url": "https://cob.sbcounty.gov/business-licenses/",
    "fire_department_name": "San Bernardino County Fire Protection District",
    "fire_department_url": "https://sbcfire.org",
    "phone": "909-387-8311",
    "email": "landuse@lus.sbcounty.gov",
    "address": "385 N Arrowhead Ave, San Bernardino, CA 92415",
    "timezone": "America/Los_Angeles",
}

REGULATIONS: List[Dict[str, Any]] = [
    {
        "regulation_type": RegulationType.ZONING.value,
        "title": "Desert Region Land Use Permit",
        "description": "Food facilities must comply with Land Use Services requirements for commercial activities in the desert region.",
        "enforcement_agency": "San Bernardino County Land Use Services",
        "agency_phone": "909-387-8311",
        "agency_url": "https://lus.sbcounty.gov",
        "requirements": {
            "site_plan_review": True,
            "water_availability_proof": True,
            "noise_mitigation_plan": False,
        },
        "applicable_facility_types": [
            FacilityType.FOOD_TRUCK.value,
            FacilityType.CATERING.value,
            FacilityType.PREP_KITCHEN.value,
        ],
    },
    {
        "regulation_type": RegulationType.HEALTH_PERMIT.value,
        "title": "San Bernardino County Health Permit",
        "description": "County-issued health permit required for any retail food operation in Joshua Tree.",
        "enforcement_agency": "San Bernardino County Environmental Health",
        "agency_url": "https://dph.sbcounty.gov/programs/ehs/food-protection/",
        "requirements": {
            "plan_review_required": True,
            "water_source_certification": True,
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.GHOST_KITCHEN.value,
        ],
    },
]

INSURANCE_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "insurance_type": "general_liability",
        "coverage_name": "General Liability",
        "description": "Required by the county for special use permits and commercial operations.",
        "minimum_coverage_amount": 1000000.0,
        "per_occurrence_limit": 1000000.0,
        "applicable_facility_types": [
            FacilityType.CATERING.value,
            FacilityType.FOOD_TRUCK.value,
        ],
        "is_mandatory": True,
    },
    {
        "insurance_type": "environmental_impairment",
        "coverage_name": "Wastewater System Coverage",
        "description": "Recommended coverage for facilities utilizing on-site wastewater treatment systems.",
        "minimum_coverage_amount": 500000.0,
        "applicable_facility_types": [
            FacilityType.PREP_KITCHEN.value,
            FacilityType.GHOST_KITCHEN.value,
        ],
        "is_mandatory": False,
    },
]

def build_payload(verification_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a DataIngestionRequest-compatible payload for Joshua Tree."""

    verification = verification_date or datetime.utcnow()
    return {
        "city_name": JURISDICTION_NAME,
        "state": STATE,
        "data_source": DATA_SOURCE,
        "verification_date": verification.isoformat(),
        "jurisdiction_info": JURISDICTION_INFO,
        "regulations": REGULATIONS,
        "insurance_requirements": INSURANCE_REQUIREMENTS,
        "opa_package": OPA_PACKAGE,
    }

__all__ = [
    "JURISDICTION_INFO",
    "REGULATIONS",
    "INSURANCE_REQUIREMENTS",
    "build_payload",
]
