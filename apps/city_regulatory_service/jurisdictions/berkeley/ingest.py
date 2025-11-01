
"""Synthetic ingestion payloads for Berkeley, California."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.city_regulatory_service.models import FacilityType, RegulationType
from . import DATA_SOURCE, JURISDICTION_NAME, OPA_PACKAGE, STATE

JURISDICTION_INFO: Dict[str, Any] = {
    "county": "Alameda County",
    "country_code": "US",
    "fips_code": "06001",
    "population": 121263,
    "health_department_name": "City of Berkeley Public Health Division",
    "health_department_url": "https://berkeleyca.gov/departments/public-health",
    "business_licensing_dept": "Finance Department - Business Licensing",
    "business_licensing_url": "https://berkeleyca.gov/construction-development/business-licensing",
    "fire_department_name": "Berkeley Fire Department",
    "fire_department_url": "https://berkeleyca.gov/safety-health/fire",
    "phone": "510-981-7460",
    "email": "publichealth@cityofberkeley.info",
    "address": "1947 Center St, Berkeley, CA 94704",
    "timezone": "America/Los_Angeles",
}

REGULATIONS: List[Dict[str, Any]] = [
    {
        "regulation_type": RegulationType.HEALTH_PERMIT.value,
        "title": "Retail Food Facility Permit",
        "description": "Food service establishments must maintain an active permit issued by the Public Health Division.",
        "local_code_reference": "Berkeley Municipal Code 9.12",
        "enforcement_agency": "Berkeley Environmental Health",
        "agency_phone": "510-981-5310",
        "agency_url": "https://berkeleyca.gov/construction-development/environmental-health",
        "requirements": {
            "inspection_frequency": "Annual",
            "hazard_analysis_plan": True,
            "temperature_log": True,
        },
        "application_process": {
            "steps": [
                "Submit application with menu and floor plan",
                "Complete pre-opening inspection",
                "Maintain updated food handler certifications",
            ]
        },
        "fees": {
            "initial": 890.0,
            "renewal": 730.0,
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.CATERING.value,
            FacilityType.FOOD_TRUCK.value,
        ],
    },
    {
        "regulation_type": RegulationType.FIRE_SAFETY.value,
        "title": "Commercial Kitchen Hood and Suppression Maintenance",
        "description": "Kitchens must maintain hood and suppression systems inspected every six months.",
        "local_code_reference": "California Fire Code Section 609",
        "enforcement_agency": "Berkeley Fire Prevention Bureau",
        "agency_phone": "510-981-3473",
        "agency_url": "https://berkeleyca.gov/safety-health/fire/fire-prevention",
        "requirements": {
            "inspection_interval_months": 6,
            "documentation_required": ["Service certificate", "Technician license"],
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.COMMISSARY.value,
            FacilityType.GHOST_KITCHEN.value,
        ],
    },
]

INSURANCE_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "insurance_type": "general_liability",
        "coverage_name": "Commercial General Liability",
        "description": "Coverage protecting against bodily injury or property damage claims arising from food operations.",
        "minimum_coverage_amount": 2000000.0,
        "per_occurrence_limit": 1000000.0,
        "aggregate_limit": 2000000.0,
        "deductible_max": 5000.0,
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.CATERING.value,
        ],
        "local_ordinance": "Berkeley Municipal Code 9.12.030",
        "is_mandatory": True,
    },
    {
        "insurance_type": "workers_compensation",
        "coverage_name": "Workers' Compensation",
        "description": "Required for any facility with one or more employees within Berkeley city limits.",
        "minimum_coverage_amount": 1000000.0,
        "aggregate_limit": 1000000.0,
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.BAKERY.value,
            FacilityType.PREP_KITCHEN.value,
        ],
        "state_requirement": "California Labor Code 3700",
        "is_mandatory": True,
    },
]

def build_payload(verification_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a DataIngestionRequest-compatible payload for Berkeley."""

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
