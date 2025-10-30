"""
New York City regulatory data ingestion adapter.

Extracts and maps regulatory requirements from NYC city portals and documents.
"""

from __future__ import annotations

from typing import Any


class NewYorkCityAdapter:
    """Adapter for ingesting New York City regulatory requirements."""

    CITY_NAME = "New York"
    STATE = "NY"

    # NYC-specific portal URLs
    PORTALS = {
        "business_licenses": "https://www1.nyc.gov/nycbusiness/",
        "health_permits": "https://www1.nyc.gov/site/doh/business/permits-and-licenses.page",
        "fire_permits": "https://www1.nyc.gov/site/fdny/business/permits-and-licenses.page",
        "dca": "https://www1.nyc.gov/site/dca/",
    }

    @classmethod
    def get_business_license_requirements(cls) -> list[dict[str, Any]]:
        """
        Extract business license requirements for NYC.

        Returns:
            List of requirement dictionaries
        """
        return [
            {
                "requirement_id": "nyc_dca_general_vendor_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "business_license",
                "agency": "NYC Department of Consumer Affairs",
                "agency_type": "licensing",
                "requirement_label": "General Vendor License",
                "applies_to": ["food truck", "mobile vendor", "caterer"],
                "required_documents": [
                    "Valid government-issued photo ID",
                    "EIN or Social Security Number",
                    "Proof of NYC address",
                    "Color photograph",
                ],
                "renewal_cycle": "biannual",
                "fee_structure": {
                    "amount": 200.00,
                    "frequency": "biannual",
                    "schedule": "flat rate",
                    "notes": "$200 for 2-year license",
                },
                "submission_channel": "in person",
                "application_url": "https://www1.nyc.gov/site/dca/businesses/license-checklist-general-vendor.page",
                "inspection_required": False,
                "official_url": cls.PORTALS["dca"],
                "rules": {
                    "restrictions": "Must not block pedestrian traffic",
                    "zones": "Restricted zones apply in certain neighborhoods",
                    "penalties": "Fines up to $1,000 for violations",
                },
            }
        ]

    @classmethod
    def get_health_permit_requirements(cls) -> list[dict[str, Any]]:
        """
        Extract health permit requirements for NYC.

        Returns:
            List of requirement dictionaries
        """
        return [
            {
                "requirement_id": "nyc_dohmh_food_service_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "restaurant_license",
                "agency": "NYC Department of Health and Mental Hygiene",
                "agency_type": "health",
                "requirement_label": "Food Service Establishment Permit",
                "applies_to": ["restaurant", "caterer", "shared kitchen", "commissary"],
                "required_documents": [
                    "Completed application",
                    "Building floor plan",
                    "Equipment specifications",
                    "Food Protection Certificate",
                    "Proposed menu",
                ],
                "renewal_cycle": "annual",
                "fee_structure": {
                    "amount": None,
                    "frequency": "annual",
                    "schedule": "variable by seating capacity",
                    "notes": "Ranges from $280 to $1,350+ based on seating and risk",
                },
                "submission_channel": "online",
                "application_url": "https://www1.nyc.gov/site/doh/business/food-operators/apply-for-a-permit.page",
                "inspection_required": True,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "inspection_schedule": "Pre-opening inspection required, then unannounced annual inspections",
                    "grading": "Letter grade (A, B, C) posted publicly",
                    "violations": "Points-based system; 28+ points = C grade",
                    "posting_requirement": "Grade card must be displayed in front window",
                },
            },
            {
                "requirement_id": "nyc_dohmh_food_protection_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "food_safety_training",
                "agency": "NYC Department of Health and Mental Hygiene",
                "agency_type": "health",
                "requirement_label": "Food Protection Certificate",
                "applies_to": ["restaurant", "caterer", "shared kitchen", "food truck"],
                "required_documents": [
                    "NYC Food Protection Course completion",
                    "Passing score on NYC DOHMH exam",
                ],
                "renewal_cycle": "triennial",
                "fee_structure": {
                    "amount": 89.00,
                    "frequency": "one-time",
                    "schedule": "per exam",
                    "notes": "Course costs vary ($100-200), exam is $89",
                },
                "submission_channel": "online",
                "application_url": "https://www1.nyc.gov/site/doh/business/food-operators/food-protection-course.page",
                "inspection_required": False,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "requirement": "At least one certified food protection supervisor on premises during all hours",
                    "exam": "Must pass NYC-specific food protection exam",
                    "renewal": "Every 5 years",
                    "languages": "Available in multiple languages",
                },
            },
            {
                "requirement_id": "nyc_dohmh_mobile_food_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "restaurant_license",
                "agency": "NYC Department of Health and Mental Hygiene",
                "agency_type": "health",
                "requirement_label": "Mobile Food Vending Permit",
                "applies_to": ["food truck", "mobile vendor"],
                "required_documents": [
                    "Vehicle registration",
                    "Food Protection Certificate",
                    "Commissary letter (base of operation)",
                    "Vehicle inspection certificate",
                ],
                "renewal_cycle": "biannual",
                "fee_structure": {
                    "amount": 200.00,
                    "frequency": "biannual",
                    "schedule": "flat rate",
                    "notes": "$200 for 2-year permit",
                },
                "submission_channel": "online",
                "application_url": "https://www1.nyc.gov/site/doh/business/food-operators/mobile-food-vendors.page",
                "inspection_required": True,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "commissary_requirement": "Must have approved commissary for food prep",
                    "parking_restrictions": "Cannot park within 20 feet of building entrance",
                    "permit_cap": "Limited number of permits available (capped)",
                },
            },
        ]

    @classmethod
    def get_insurance_requirements(cls) -> list[dict[str, Any]]:
        """
        Extract insurance requirements for NYC.

        Returns:
            List of requirement dictionaries
        """
        return [
            {
                "requirement_id": "nyc_insurance_general_liability_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "insurance",
                "agency": "NYC Department of Health and Mental Hygiene",
                "agency_type": "health",
                "requirement_label": "General Liability Insurance",
                "applies_to": ["restaurant", "caterer", "shared kitchen", "food truck"],
                "required_documents": [
                    "Certificate of Insurance",
                    "Policy must list business address",
                ],
                "renewal_cycle": "annual",
                "fee_structure": {
                    "amount": None,
                    "frequency": "annual",
                    "schedule": "varies by provider",
                    "notes": "Typical annual premium: $500-3,000+",
                },
                "submission_channel": "mail or online",
                "application_url": None,
                "inspection_required": False,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "minimum_coverage": {
                        "general_liability": "$1,000,000 per occurrence",
                        "aggregate": "$2,000,000",
                        "workers_comp": "Required if employees",
                    },
                    "requirements": [
                        "Must be maintained throughout operation",
                        "Proof required for permit renewal",
                    ],
                },
            }
        ]

    @classmethod
    def get_all_requirements(cls) -> list[dict[str, Any]]:
        """
        Get all NYC regulatory requirements.

        Returns:
            Complete list of requirements
        """
        requirements = []
        requirements.extend(cls.get_business_license_requirements())
        requirements.extend(cls.get_health_permit_requirements())
        requirements.extend(cls.get_insurance_requirements())
        return requirements


__all__ = ["NewYorkCityAdapter"]
