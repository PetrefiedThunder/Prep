"""Synthetic ingestion payloads for Palo Alto, California."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from apps.city_regulatory_service.models import FacilityType, RegulationType
from . import DATA_SOURCE, JURISDICTION_NAME, OPA_PACKAGE, STATE

JURISDICTION_INFO: Dict[str, Any] = {
    "county": "Santa Clara County",
    "country_code": "US",
    "fips_code": "06085",
    "population": 68924,
    "health_department_name": "Santa Clara County Public Health",
    "health_department_url": "https://publichealth.sccgov.org",
    "business_licensing_dept": "Palo Alto Revenue Division",
    "business_licensing_url": "https://www.cityofpaloalto.org/Departments/Administrative-Services/Revenue-Division",
    "fire_department_name": "Palo Alto Fire Department",
    "fire_department_url": "https://www.cityofpaloalto.org/Departments/Fire",
    "phone": "650-329-2271",
    "email": "revenue@cityofpaloalto.org",
    "address": "250 Hamilton Ave, Palo Alto, CA 94301",
    "timezone": "America/Los_Angeles",
}

REGULATIONS: List[Dict[str, Any]] = [
    {
        "regulation_type": RegulationType.BUSINESS_LICENSE.value,
        "title": "Business Registration Certificate",
        "description": "All businesses operating in Palo Alto must obtain an annual business registration certificate.",
        "enforcement_agency": "Palo Alto Administrative Services",
        "agency_phone": "650-329-2271",
        "agency_url": "https://www.cityofpaloalto.org/Departments/Administrative-Services/Revenue-Division",
        "requirements": {
            "renewal_frequency": "Annual",
            "gross_receipts_reporting": True,
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.BAKERY.value,
            FacilityType.COMMERCIAL_KITCHEN.value,
        ],
    },
    {
        "regulation_type": RegulationType.FIRE_SAFETY.value,
        "title": "Vegetation Management and Fire Code Compliance",
        "description": "Commercial kitchens must maintain defensible space and comply with the California Fire Code as adopted by Palo Alto.",
        "enforcement_agency": "Palo Alto Fire Prevention Bureau",
        "agency_url": "https://www.cityofpaloalto.org/Departments/Fire/Fire-Prevention",
        "requirements": {
            "annual_inspection": True,
            "grease_duct_cleaning_interval_months": 6,
        },
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.GHOST_KITCHEN.value,
            FacilityType.CATERING.value,
        ],
    },
]

INSURANCE_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "insurance_type": "general_liability",
        "coverage_name": "General Liability Coverage",
        "description": "Required as part of Palo Alto's business registration for customer-facing establishments.",
        "minimum_coverage_amount": 1000000.0,
        "per_occurrence_limit": 1000000.0,
        "aggregate_limit": 2000000.0,
        "applicable_facility_types": [
            FacilityType.RESTAURANT.value,
            FacilityType.BAKERY.value,
        ],
        "is_mandatory": True,
    },
    {
        "insurance_type": "property",
        "coverage_name": "Property Insurance",
        "description": "Facilities must maintain property coverage for fire and water damage risks.",
        "minimum_coverage_amount": 500000.0,
        "applicable_facility_types": [
            FacilityType.COMMERCIAL_KITCHEN.value,
            FacilityType.PREP_KITCHEN.value,
        ],
        "is_mandatory": False,
    },
]

def build_payload(verification_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a DataIngestionRequest-compatible payload for Palo Alto."""

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
