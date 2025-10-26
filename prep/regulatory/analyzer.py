"""Lightweight compliance analyzer used by the Prep API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Sequence


class ComplianceLevel(str, Enum):
    """Overall compliance score for a kitchen."""

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
