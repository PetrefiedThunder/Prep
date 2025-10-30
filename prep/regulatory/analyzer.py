"""Compliance analysis utilities for commercial kitchens."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Sequence


class ComplianceLevel(str, Enum):
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
    last_analyzed: datetime
    kitchen_id: str = "unknown"
    state: str | None = None
    city: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegulatoryAnalyzer:
    """Naive regulatory analyzer that evaluates a kitchen against basic rules."""

    REQUIRED_FIELDS: Dict[str, str] = {
        "health_permit_number": "Active health permit",
        "last_inspection_date": "Recent health inspection on file",
        "insurance": "Valid liability insurance",
        "zoning_type": "Approved zoning classification",
    }
    DELIVERY_PERMIT_SLUGS = {"delivery_only", "ghost_kitchen", "virtual_kitchen"}

    async def analyze_kitchen_compliance(
        self,
        kitchen_data: Dict[str, Any],
        regulations: Sequence[Dict[str, Any]] | None = None,
    ) -> ComplianceAnalysis:
        """Compute a compliance snapshot for a kitchen."""

        regulations = regulations or []
        missing_requirements: List[str] = []
        recommendations: List[str] = []
        metadata: Dict[str, Any] = {}

        for field, description in self.REQUIRED_FIELDS.items():
            value = kitchen_data.get(field)
            if not value:
                missing_requirements.append(description)
                recommendations.append(f"Provide documentation for: {description}.")

        for item in regulations:
            guidance = item.get("guidance") or item.get("description")
            if guidance and guidance not in recommendations:
                recommendations.append(guidance)

        permit_types = [str(item).lower() for item in kitchen_data.get("permit_types", [])]
        if not permit_types:
            missing_requirements.append("Permit types not documented")
            recommendations.append("Upload the current set of operating permits.")
        elif kitchen_data.get("delivery_only"):
            has_delivery_permit = any(
                slug in self.DELIVERY_PERMIT_SLUGS for slug in permit_types
            )
            if not has_delivery_permit:
                missing_requirements.append("Delivery-only kitchens must provide ghost kitchen permit")
                recommendations.append(
                    "Add the delivery/ghost kitchen permit to the permit_types metadata."
                )

        sanitation_logs = kitchen_data.get("sanitation_logs") or []
        latest_log: Dict[str, Any] | None = None
        if sanitation_logs:
            sorted_logs = sorted(
                sanitation_logs,
                key=lambda item: item.get("logged_at") or datetime.min,
                reverse=True,
            )
            latest_log = sorted_logs[0]
            last_logged_at = latest_log.get("logged_at")
            if isinstance(last_logged_at, datetime):
                metadata["last_sanitation_log"] = last_logged_at.isoformat()
                if datetime.utcnow() - last_logged_at > timedelta(days=7):
                    missing_requirements.append("Sanitation log older than 7 days")
                    recommendations.append("Upload the latest sanitation walkthrough results.")
            status = str(latest_log.get("status", "")).lower()
            if status not in {"passed", "satisfactory", "clean"}:
                missing_requirements.append("Most recent sanitation check did not pass")
                recommendations.append("Schedule a follow-up sanitation inspection and upload the results.")
            if latest_log.get("follow_up_required"):
                recommendations.append("Resolve outstanding sanitation follow-up items and document completion.")
        else:
            missing_requirements.append("Sanitation logs missing")
            recommendations.append("Record a sanitation checklist entry for this kitchen.")

        risk_score = max(0, 100 - 15 * len(missing_requirements))

        if not kitchen_data.get("state"):
            missing_requirements.append("Kitchen location missing state metadata")
            risk_score = min(risk_score, 60)

        if not kitchen_data.get("city"):
            recommendations.append("Add city information so we can match municipal codes.")

        if missing_requirements:
            overall = (
                ComplianceLevel.NON_COMPLIANT
                if len(missing_requirements) > 2
                else ComplianceLevel.PARTIAL
            )
        else:
            overall = (
                ComplianceLevel.COMPLIANT
                if kitchen_data.get("state")
                else ComplianceLevel.UNKNOWN
            )

        return ComplianceAnalysis(
            overall_compliance=overall,
            risk_score=risk_score,
            missing_requirements=missing_requirements,
            recommendations=recommendations,
            last_analyzed=datetime.utcnow(),
            kitchen_id=str(kitchen_data.get("id", "unknown")),
            state=kitchen_data.get("state"),
            city=kitchen_data.get("city"),
            metadata=metadata,
        )


__all__ = ["ComplianceAnalysis", "ComplianceLevel", "RegulatoryAnalyzer"]
