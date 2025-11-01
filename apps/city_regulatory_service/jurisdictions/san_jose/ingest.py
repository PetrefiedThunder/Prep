"""Synthetic ingestion payloads for San Jose, California."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.city_regulatory_service.models import FacilityType, RegulationType
from . import DATA_SOURCE, JURISDICTION_NAME, OPA_PACKAGE, STATE

JURISDICTION_INFO: Dict[str, Any] = {
    "county": "Santa Clara County",
    "country_code": "US",
    "fips_code": "06085",
    "population": 1013240,
    "health_department_name": "Santa Clara County Department of Environmental Health",
    "health_department_url": "https://ehinfo.sccgov.org/food-safety",
    "business_licensing_dept": "San José Office of Economic Development",
    "business_licensing_url": "https://www.sanjoseca.gov/your-government/departments/finance/business-tax",
    "fire_department_name": "San José Fire Department",
    "fire_department_url": "https://www.sanjoseca.gov/your-government/departments/fire",
    "phone": "408-535-7770",
    "email": "oed@sanjoseca.gov",
    "address": "200 E Santa Clara St, San Jose, CA 95113",
    "timezone": "America/Los_Angeles",
}

REGULATIONS: List[Dict[str, Any]] = [
    {
        "regulation_type": RegulationType.HEALTH_PERMIT.value,
        "title": "Food Facility Permit",
        "description": "Food facilities must secure a permit from the County Department of Environmental Health before operation.",
        "enforcement_agency": "Santa Clara County DEH",
        "agency_phone": "408-918-3400",
        "agency_url": "https://ehinfo.sccgov.org/permits-forms/food-program",
        "requirements": {
            "plan_review_required": True,
            "annual_inspection": True,
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.BAKERY.value,
            FacilityType.FOOD_TRUCK.value,
        ],
        "fees": {
            "initial": 1045.0,
            "renewal": 890.0,
        },
    },
    {
        "regulation_type": RegulationType.WASTE_MANAGEMENT.value,
        "title": "Organics Recycling Compliance",
        "description": "Businesses must subscribe to organics collection service and maintain separation of organic waste streams.",
        "enforcement_agency": "City of San José Environmental Services",
        "agency_url": "https://www.sanjoseca.gov/your-government/environment/waste-recycling",
        "requirements": {
            "organics_service": True,
            "employee_training": "Annual",
            "recordkeeping_months": 24,
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.COMMISSARY.value,
            FacilityType.CATERING.value,
        ],
    },
]

INSURANCE_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "insurance_type": "general_liability",
        "coverage_name": "Commercial General Liability",
        "description": "Covers claims of bodily injury or property damage occurring at the facility.",
        "minimum_coverage_amount": 2000000.0,
        "per_occurrence_limit": 1000000.0,
        "aggregate_limit": 2000000.0,
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.CATERING.value,
            FacilityType.GHOST_KITCHEN.value,
        ],
        "local_ordinance": "San José Municipal Code 4.46.050",
        "is_mandatory": True,
    },
    {
        "insurance_type": "automobile_liability",
        "coverage_name": "Commercial Auto Liability",
        "description": "Mobile food facilities must maintain automobile liability coverage for each permitted vehicle.",
        "minimum_coverage_amount": 1000000.0,
        "per_occurrence_limit": 1000000.0,
        "applicable_facility_types": [
            FacilityType.FOOD_TRUCK.value,
            FacilityType.CATERING.value,
        ],
        "local_ordinance": "San José Municipal Code 6.54",
        "is_mandatory": True,
    },
]

def build_payload(verification_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a DataIngestionRequest-compatible payload for San Jose."""

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
