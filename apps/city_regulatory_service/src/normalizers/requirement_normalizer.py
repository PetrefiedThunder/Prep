"""
Normalizer for city regulatory requirements.

Converts diverse city-specific regulatory data into a standardized format
using a shared jurisdictional ontology and requirement taxonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


# ============================================================================
# Requirement Type Taxonomy
# ============================================================================

REQUIREMENT_TYPES = {
    "business_license": [
        "business registration certificate",
        "business license",
        "business tax certificate",
        "general business license",
    ],
    "restaurant_license": [
        "restaurant permit",
        "food service permit",
        "food establishment permit",
        "retail food permit",
        "common victualler license",
    ],
    "food_safety_training": [
        "food manager certification",
        "food handler certificate",
        "food safety manager",
        "servsafe certification",
    ],
    "health_permit": [
        "health permit",
        "health department permit",
        "sanitation permit",
        "food safety permit",
    ],
    "insurance": [
        "general liability insurance",
        "workers compensation",
        "commercial insurance",
        "liability coverage",
    ],
    "inspection": [
        "health inspection",
        "fire inspection",
        "safety inspection",
        "initial inspection",
    ],
    "zoning": [
        "zoning approval",
        "conditional use permit",
        "zoning compliance",
    ],
    "building": [
        "building permit",
        "construction permit",
        "alteration permit",
    ],
    "fire_safety": [
        "fire permit",
        "fire safety certificate",
        "fire clearance",
    ],
}


RENEWAL_FREQUENCIES = {
    "annual": ["annual", "yearly", "1 year", "12 months"],
    "biannual": ["biannual", "twice yearly", "6 months", "semi-annual"],
    "triennial": ["triennial", "every 3 years", "3 years"],
    "on_event": ["on inspection", "as needed", "event-based"],
    "perpetual": ["permanent", "one-time", "perpetual", "no renewal"],
}


SUBMISSION_CHANNELS = {
    "online": ["online", "web portal", "electronic", "digital"],
    "mail": ["mail", "postal", "by mail"],
    "in_person": ["in person", "walk-in", "counter", "office"],
    "hybrid": ["online or in-person", "multiple options"],
}


BUSINESS_TYPES = [
    "shared kitchen",
    "ghost kitchen",
    "restaurant",
    "food truck",
    "mobile vendor",
    "caterer",
    "bakery",
    "food manufacturer",
    "commissary",
]


# ============================================================================
# Normalized Data Structure
# ============================================================================

@dataclass
class NormalizedRequirement:
    """Normalized city regulatory requirement."""

    # Identifiers
    requirement_id: str
    jurisdiction: str
    normalized_type: str

    # Basic info
    requirement_label: str
    governing_agency: str
    agency_type: str

    # Rules
    required_documents: list[str]
    submission_channel: str
    application_url: Optional[str]

    # Compliance
    inspection_required: bool
    renewal_frequency: str
    fee_amount: Optional[float]
    fee_schedule: str

    # Applicability
    applies_to: list[str]

    # Source
    source_url: str
    last_updated: datetime

    # Additional metadata
    rules: dict[str, Any]


# ============================================================================
# Normalization Functions
# ============================================================================

class RequirementNormalizer:
    """Normalizes raw city requirement data into standardized format."""

    @staticmethod
    def normalize_requirement_type(raw_label: str) -> str:
        """
        Map raw requirement label to normalized type.

        Args:
            raw_label: Raw requirement name from source

        Returns:
            Normalized requirement type
        """
        raw_lower = raw_label.lower()

        for normalized_type, variants in REQUIREMENT_TYPES.items():
            for variant in variants:
                if variant in raw_lower:
                    return normalized_type

        # Default fallback
        return "other"

    @staticmethod
    def normalize_renewal_frequency(raw_frequency: str) -> str:
        """
        Map raw renewal frequency to normalized value.

        Args:
            raw_frequency: Raw frequency string from source

        Returns:
            Normalized frequency
        """
        if not raw_frequency:
            return "unknown"

        raw_lower = raw_frequency.lower()

        for normalized, variants in RENEWAL_FREQUENCIES.items():
            for variant in variants:
                if variant in raw_lower:
                    return normalized

        return "unknown"

    @staticmethod
    def normalize_submission_channel(raw_channel: str) -> str:
        """
        Map raw submission channel to normalized value.

        Args:
            raw_channel: Raw channel string from source

        Returns:
            Normalized submission channel
        """
        if not raw_channel:
            return "unknown"

        raw_lower = raw_channel.lower()

        for normalized, variants in SUBMISSION_CHANNELS.items():
            for variant in variants:
                if variant in raw_lower:
                    return normalized

        return "unknown"

    @staticmethod
    def normalize_business_types(raw_types: list[str]) -> list[str]:
        """
        Normalize business type applicability.

        Args:
            raw_types: Raw business type list

        Returns:
            Normalized business type list
        """
        normalized = []

        for raw_type in raw_types:
            raw_lower = raw_type.lower()

            for business_type in BUSINESS_TYPES:
                if business_type in raw_lower or raw_lower in business_type:
                    if business_type not in normalized:
                        normalized.append(business_type)

        return normalized or ["all"]

    @staticmethod
    def normalize_agency_name(raw_agency: str, city: str) -> str:
        """
        Normalize agency names for consistency.

        Args:
            raw_agency: Raw agency name
            city: City name for context

        Returns:
            Normalized agency name
        """
        # Common abbreviations
        replacements = {
            "Department of Public Health": "DPH",
            "Health Department": "Health Dept",
            "Office of the Treasurer": "Treasurer",
            "Tax Collector": "Tax Collection",
        }

        normalized = raw_agency
        for full, abbrev in replacements.items():
            if full in raw_agency:
                normalized = raw_agency.replace(full, abbrev)

        return normalized

    @staticmethod
    def extract_fee_amount(fee_data: dict[str, Any]) -> tuple[Optional[float], str]:
        """
        Extract normalized fee amount and schedule.

        Args:
            fee_data: Raw fee information

        Returns:
            Tuple of (amount, schedule description)
        """
        if not fee_data:
            return None, "unknown"

        amount = fee_data.get("amount")
        if isinstance(amount, (int, float)):
            amount = float(amount)
        else:
            amount = None

        schedule = fee_data.get("frequency", fee_data.get("schedule", "unknown"))

        return amount, schedule

    @classmethod
    def normalize(cls, raw_data: dict[str, Any]) -> NormalizedRequirement:
        """
        Normalize a raw city requirement into standardized format.

        Args:
            raw_data: Raw requirement data from ingestion adapter

        Returns:
            NormalizedRequirement object
        """
        jurisdiction = raw_data.get("jurisdiction", "Unknown")
        requirement_label = raw_data.get("requirement_label", "")

        # Normalize core fields
        normalized_type = cls.normalize_requirement_type(requirement_label)
        renewal_frequency = cls.normalize_renewal_frequency(
            raw_data.get("renewal_cycle", "")
        )
        submission_channel = cls.normalize_submission_channel(
            raw_data.get("submission_channel", "")
        )

        # Normalize business types
        raw_applies_to = raw_data.get("applies_to", [])
        applies_to = cls.normalize_business_types(raw_applies_to)

        # Normalize agency
        raw_agency = raw_data.get("agency", "Unknown Agency")
        governing_agency = cls.normalize_agency_name(raw_agency, jurisdiction)

        # Extract fee info
        fee_data = raw_data.get("fee_structure", {})
        if isinstance(fee_data, dict):
            fee_amount, fee_schedule = cls.extract_fee_amount(fee_data)
        else:
            fee_amount, fee_schedule = None, str(fee_data) if fee_data else "unknown"

        # Build rules object
        rules = raw_data.get("rules", {})
        if not isinstance(rules, dict):
            rules = {}

        # Ensure required documents is a list
        required_documents = raw_data.get("required_documents", [])
        if not isinstance(required_documents, list):
            required_documents = [str(required_documents)]

        return NormalizedRequirement(
            requirement_id=raw_data.get("requirement_id", f"{jurisdiction.lower().replace(' ', '_')}_{normalized_type}"),
            jurisdiction=jurisdiction,
            normalized_type=normalized_type,
            requirement_label=requirement_label,
            governing_agency=governing_agency,
            agency_type=raw_data.get("agency_type", "health"),
            required_documents=required_documents,
            submission_channel=submission_channel,
            application_url=raw_data.get("application_url"),
            inspection_required=raw_data.get("inspection_required", False),
            renewal_frequency=renewal_frequency,
            fee_amount=fee_amount,
            fee_schedule=fee_schedule,
            applies_to=applies_to,
            source_url=raw_data.get("source_url", raw_data.get("official_url", "")),
            last_updated=datetime.utcnow(),
            rules=rules,
        )


__all__ = ["RequirementNormalizer", "NormalizedRequirement"]
