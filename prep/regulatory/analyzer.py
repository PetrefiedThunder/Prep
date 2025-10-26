"""Lightweight compliance analyzer used by the Prep API."""
"""Compliance analysis utilities for commercial kitchens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Sequence


class ComplianceLevel(str, Enum):
    """Overall compliance score for a kitchen."""
from typing import Dict, List


class ComplianceLevel(Enum):
    """Enumerated compliance levels returned by the analyzer."""

    COMPLIANT = "compliant"
    PARTIAL = "partial_compliance"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ComplianceAnalysis:
    """Result returned by the regulatory analyzer."""

    overall_compliance: ComplianceLevel
    risk_score: int
    missing_requirements: List[str]
    recommendations: List[str]
    """Summary of a compliance check for a kitchen."""

    kitchen_id: str
    state: str
    city: str
    overall_compliance: ComplianceLevel
    missing_requirements: List[str]
    recommendations: List[str]
    risk_score: int
    last_analyzed: datetime


class RegulatoryAnalyzer:
    """Naive regulatory analyzer that evaluates a kitchen against basic rules."""

    REQUIRED_FIELDS: Dict[str, str] = {
        "health_permit_number": "Active health permit",
        "last_inspection_date": "Recent health inspection on file",
        "insurance": "Valid liability insurance",
        "zoning_type": "Approved zoning classification",
    }

    async def analyze_kitchen_compliance(
        self,
        kitchen_data: Dict[str, Any],
        regulations: Sequence[Dict[str, Any]] | None = None,
    ) -> ComplianceAnalysis:
        """Compute a compliance snapshot for a kitchen."""

        regulations = regulations or []
        missing_requirements: List[str] = []
        recommendations: List[str] = []

        # Inspect required fields and mark those that are absent.
        for field, description in self.REQUIRED_FIELDS.items():
            value = kitchen_data.get(field)
            if not value:
                missing_requirements.append(description)
                recommendations.append(f"Provide documentation for: {description}.")

        # Derive a naive risk score out of 100.
        base_risk = 100
        penalty_per_issue = 20
        risk_score = max(base_risk - penalty_per_issue * len(missing_requirements), 0)

        # Enrich recommendations using jurisdiction specific regulations.
        for item in regulations:
            guidance = item.get("guidance") or item.get("description")
            if guidance and guidance not in recommendations:
                recommendations.append(guidance)

        if not kitchen_data.get("state"):
            missing_requirements.append("Kitchen location missing state metadata")
            risk_score = min(risk_score, 60)

        if not kitchen_data.get("city"):
            recommendations.append("Add city information so we can match municipal codes.")

        if missing_requirements:
            overall = ComplianceLevel.NON_COMPLIANT if len(missing_requirements) > 2 else ComplianceLevel.PARTIAL
        else:
            overall = ComplianceLevel.COMPLIANT if kitchen_data.get("state") else ComplianceLevel.UNKNOWN

        return ComplianceAnalysis(
            overall_compliance=overall,
            risk_score=risk_score,
            missing_requirements=missing_requirements,
            recommendations=recommendations,
            last_analyzed=datetime.utcnow(),
        )


__all__ = [
    "ComplianceAnalysis",
    "ComplianceLevel",
    "RegulatoryAnalyzer",
]
    """Apply regulatory rules to individual kitchens."""

    def __init__(self) -> None:
        self.risk_factors = {
            "health_permit": 40,
            "insurance": 30,
            "zoning": 20,
            "fire_safety": 10,
        }

    async def analyze_kitchen_compliance(
        self, kitchen_data: Dict, regulations: List[Dict]
    ) -> ComplianceAnalysis:
        """Analyze kitchen compliance against regulations."""

        missing_requirements: List[str] = []
        risk_score = 0

        health_compliant = await self._check_health_compliance(kitchen_data, regulations)
        if not health_compliant:
            missing_requirements.append("Health department permit")
            risk_score += self.risk_factors["health_permit"]

        insurance_compliant = await self._check_insurance_compliance(kitchen_data, regulations)
        if not insurance_compliant:
            missing_requirements.append("Adequate insurance coverage")
            risk_score += self.risk_factors["insurance"]

        zoning_compliant = await self._check_zoning_compliance(kitchen_data, regulations)
        if not zoning_compliant:
            missing_requirements.append("Zoning compliance")
            risk_score += self.risk_factors["zoning"]

        if risk_score == 0:
            compliance_level = ComplianceLevel.COMPLIANT
        elif risk_score < 50:
            compliance_level = ComplianceLevel.PARTIAL
        else:
            compliance_level = ComplianceLevel.NON_COMPLIANT

        recommendations = await self._generate_recommendations(missing_requirements, kitchen_data)

        return ComplianceAnalysis(
            kitchen_id=kitchen_data.get("id", "unknown"),
            state=kitchen_data.get("state", "unknown"),
            city=kitchen_data.get("city", "unknown"),
            overall_compliance=compliance_level,
            missing_requirements=missing_requirements,
            recommendations=recommendations,
            risk_score=risk_score,
            last_analyzed=datetime.utcnow(),
        )

    async def _check_health_compliance(self, kitchen_data: Dict, regulations: List[Dict]) -> bool:
        """Check health department compliance."""

        health_regs = [r for r in regulations if r.get("regulation_type") == "health_permit"]

        has_permit = kitchen_data.get("health_permit_number") is not None
        recent_inspection = kitchen_data.get("last_inspection_date")

        if recent_inspection:
            inspection_date = datetime.fromisoformat(recent_inspection)
            one_year_ago = datetime.utcnow().replace(year=datetime.utcnow().year - 1)
            inspection_current = inspection_date > one_year_ago
        else:
            inspection_current = False

        return bool(has_permit and inspection_current and health_regs)

    async def _check_insurance_compliance(self, kitchen_data: Dict, regulations: List[Dict]) -> bool:
        """Check insurance compliance."""

        insurance_info = kitchen_data.get("insurance", {})
        has_liability = insurance_info.get("general_liability") is not None
        adequate_coverage = insurance_info.get("coverage_amount", 0) >= 1_000_000
        return bool(has_liability and adequate_coverage)

    async def _check_zoning_compliance(self, kitchen_data: Dict, regulations: List[Dict]) -> bool:
        """Check zoning compliance."""

        zone_type = kitchen_data.get("zoning_type", "unknown")
        return zone_type.lower() in {"commercial", "industrial", "mixed_use"}

    async def _generate_recommendations(
        self, missing_requirements: List[str], kitchen_data: Dict
    ) -> List[str]:
        """Generate specific recommendations based on missing requirements."""

        recommendations: List[str] = []
        for requirement in missing_requirements:
            lower_req = requirement.lower()
            if "health" in lower_req:
                recommendations.extend(
                    [
                        "Apply for health department permit at local health department",
                        "Schedule initial inspection with health department",
                    ]
                )
            elif "insurance" in lower_req:
                recommendations.extend(
                    [
                        "Obtain commercial liability insurance with minimum $1M coverage",
                        "Consider additional coverage for equipment and business interruption",
                    ]
                )
            elif "zoning" in lower_req:
                recommendations.extend(
                    [
                        "Verify zoning compliance with local planning department",
                        "Apply for conditional use permit if required",
                    ]
                )

        return recommendations


__all__ = ["ComplianceLevel", "ComplianceAnalysis", "RegulatoryAnalyzer"]
