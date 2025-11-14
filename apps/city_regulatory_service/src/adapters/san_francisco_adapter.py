"""
San Francisco city regulatory data ingestion adapter.

Extracts and maps regulatory requirements from SF city portals and documents.
"""

from __future__ import annotations

from typing import Any


class SanFranciscoAdapter:
    """Adapter for ingesting San Francisco regulatory requirements."""

    CITY_NAME = "San Francisco"
    STATE = "CA"

    # SF-specific portal URLs
    PORTALS = {
        "business_registration": "https://sftreasurer.org/business",
        "health_permits": "https://www.sfdph.org/dph/EH/Food/default.asp",
        "fire_permits": "https://sf-fire.org/permits",
        "planning": "https://sfplanning.org/",
    }

    @classmethod
    def get_business_license_requirements(cls) -> list[dict[str, Any]]:
        """
        Extract business license requirements for SF.

        Returns:
            List of requirement dictionaries
        """
        return [
            {
                "requirement_id": "sf_treasurer_business_registration_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "business_license",
                "agency": "SF Office of the Treasurer & Tax Collector",
                "agency_type": "licensing",
                "requirement_label": "Business Registration Certificate",
                "applies_to": ["shared kitchen", "restaurant", "caterer", "food truck"],
                "required_documents": [
                    "Proof of EIN (Federal Tax ID)",
                    "Commercial lease or proof of location",
                    "Owner identification",
                ],
                "renewal_cycle": "annual",
                "fee_structure": {
                    "amount": None,  # Variable by revenue
                    "frequency": "annual",
                    "schedule": "variable by revenue",
                    "notes": "$91.25 minimum + additional fees based on gross receipts",
                    "tiers": [
                        {
                            "threshold": "up to $50k gross receipts",
                            "fee": 91.25,
                        },
                        {
                            "threshold": "$50k-$250k gross receipts",
                            "fee": 180.50,
                        },
                        {
                            "threshold": "$250k-$500k gross receipts",
                            "fee": 306.00,
                        },
                        {
                            "threshold": "over $500k gross receipts",
                            "fee": 500.00,
                        },
                    ],
                },
                "submission_channel": "online",
                "application_url": "https://sftreasurer.org/registration",
                "inspection_required": False,
                "official_url": cls.PORTALS["business_registration"],
                "rules": {
                    "deadline": "Within 15 days of starting business",
                    "penalties": "Late fees apply after deadline",
                    "special_notes": "Home-based businesses have different requirements",
                },
            }
        ]

    @classmethod
    def get_health_permit_requirements(cls) -> list[dict[str, Any]]:
        """
        Extract health permit requirements for SF.

        Returns:
            List of requirement dictionaries
        """
        return [
            {
                "requirement_id": "sf_dph_food_permit_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "restaurant_license",
                "agency": "San Francisco Department of Public Health",
                "agency_type": "health",
                "requirement_label": "Retail Food Establishment Permit",
                "applies_to": ["shared kitchen", "restaurant", "caterer", "commissary"],
                "required_documents": [
                    "Floor plan (to scale)",
                    "Employee list",
                    "Food Manager Certification",
                    "Equipment list",
                    "Menu",
                ],
                "renewal_cycle": "annual",
                "fee_structure": {
                    "amount": 686.00,
                    "frequency": "annual",
                    "schedule": "flat rate",
                    "notes": "Fee varies by facility type and size",
                },
                "submission_channel": "online",
                "application_url": "https://www.sfdph.org/dph/EH/Food/FoodPermit.asp",
                "inspection_required": True,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "initial_inspection": "Required before permit issuance",
                    "ongoing_inspections": "Unannounced inspections 1-3 times per year",
                    "score_requirements": "Must maintain minimum score of 70",
                    "penalties": "Permit suspension if score falls below 70",
                },
            },
            {
                "requirement_id": "sf_dph_food_manager_cert_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "food_safety_training",
                "agency": "San Francisco Department of Public Health",
                "agency_type": "health",
                "requirement_label": "Food Manager Certification",
                "applies_to": ["shared kitchen", "restaurant", "caterer", "food truck"],
                "required_documents": [
                    "ANSI-accredited Food Protection Manager Certification",
                    "Certificate must be from approved provider (ServSafe, Prometric, etc.)",
                ],
                "renewal_cycle": "triennial",
                "fee_structure": {
                    "amount": None,
                    "frequency": "one-time",
                    "schedule": "varies by provider",
                    "notes": "Typically $150-200 for exam and course",
                },
                "submission_channel": "online",
                "application_url": "https://www.sfdph.org/dph/EH/Food/FoodManager.asp",
                "inspection_required": False,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "requirement": "At least one certified food manager on site during all hours",
                    "exam": "Must pass ANSI-accredited exam",
                    "renewal": "Every 3 years",
                },
            },
        ]

    @classmethod
    def get_insurance_requirements(cls) -> list[dict[str, Any]]:
        """
        Extract insurance requirements for SF.

        Returns:
            List of requirement dictionaries
        """
        return [
            {
                "requirement_id": "sf_insurance_general_liability_001",
                "jurisdiction": cls.CITY_NAME,
                "requirement_type": "insurance",
                "agency": "San Francisco Department of Public Health",
                "agency_type": "health",
                "requirement_label": "General Liability Insurance",
                "applies_to": ["shared kitchen", "restaurant", "caterer"],
                "required_documents": [
                    "Certificate of Insurance (COI)",
                    "Policy must name SF DPH as additional insured",
                ],
                "renewal_cycle": "annual",
                "fee_structure": {
                    "amount": None,
                    "frequency": "annual",
                    "schedule": "varies by provider",
                    "notes": "Premium varies based on business size and risk",
                },
                "submission_channel": "mail or online",
                "application_url": None,
                "inspection_required": False,
                "official_url": cls.PORTALS["health_permits"],
                "rules": {
                    "minimum_coverage": {
                        "general_liability": "$1,000,000 per occurrence",
                        "aggregate": "$2,000,000",
                    },
                    "requirements": [
                        "Must be from AM Best A-rated carrier",
                        "Policy must be active before permit issuance",
                    ],
                },
            }
        ]

    @classmethod
    def get_all_requirements(cls) -> list[dict[str, Any]]:
        """
        Get all SF regulatory requirements.

        Returns:
            Complete list of requirements
        """
        requirements = []
        requirements.extend(cls.get_business_license_requirements())
        requirements.extend(cls.get_health_permit_requirements())
        requirements.extend(cls.get_insurance_requirements())
        return requirements


__all__ = ["SanFranciscoAdapter"]
