"""Compliance analysis utilities for commercial kitchens."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any


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
    missing_requirements: list[str]
    recommendations: list[str]
    last_analyzed: datetime
    kitchen_id: str = "unknown"
    state: str | None = None
    city: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RegulatoryAnalyzer:
    """Naive regulatory analyzer that evaluates a kitchen against basic rules."""

    REQUIRED_FIELDS: dict[str, str] = {
        "health_permit_number": "Active health permit",
        "last_inspection_date": "Recent health inspection on file",
        "insurance": "Valid liability insurance",
        "zoning_type": "Approved zoning classification",
    }
    DELIVERY_PERMIT_SLUGS = {"delivery_only", "ghost_kitchen", "virtual_kitchen"}

    async def analyze_kitchen_compliance(
        self,
        kitchen_data: dict[str, Any],
        regulations: Sequence[dict[str, Any]] | None = None,
        *,
        pilot_mode: bool = False,
    ) -> ComplianceAnalysis:
        """Compute a compliance snapshot for a kitchen."""

        regulations = regulations or []
        missing_requirements: list[str] = []
        recommendations: list[str] = []
        metadata: dict[str, Any] = {}
        warnings: list[str] = []

        def _record_issue(
            message: str,
            recommendation: str | None = None,
            *,
            document_gap: bool,
        ) -> None:
            if recommendation and recommendation not in recommendations:
                recommendations.append(recommendation)
            if pilot_mode and document_gap:
                if message not in warnings:
                    warnings.append(message)
            else:
                if message not in missing_requirements:
                    missing_requirements.append(message)

        for field, description in self.REQUIRED_FIELDS.items():
            value = kitchen_data.get(field)
            if not value:
                _record_issue(
                    description,
                    f"Provide documentation for: {description}.",
                    document_gap=True,
                )

        for item in regulations:
            guidance = item.get("guidance") or item.get("description")
            if guidance and guidance not in recommendations:
                recommendations.append(guidance)

        permit_types = [str(item).lower() for item in kitchen_data.get("permit_types", [])]
        if not permit_types:
            _record_issue(
                "Permit types not documented",
                "Upload the current set of operating permits.",
                document_gap=True,
            )
        elif kitchen_data.get("delivery_only"):
            has_delivery_permit = any(slug in self.DELIVERY_PERMIT_SLUGS for slug in permit_types)
            if not has_delivery_permit:
                _record_issue(
                    "Delivery-only kitchens must provide ghost kitchen permit",
                    "Add the delivery/ghost kitchen permit to the permit_types metadata.",
                    document_gap=True,
                )

        sanitation_logs = kitchen_data.get("sanitation_logs") or []
        latest_log: dict[str, Any] | None = None
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
                if datetime.now(UTC) - last_logged_at > timedelta(days=7):
                    _record_issue(
                        "Sanitation log older than 7 days",
                        "Upload the latest sanitation walkthrough results.",
                        document_gap=True,
                    )
            status = str(latest_log.get("status", "")).lower()
            if status not in {"passed", "satisfactory", "clean"}:
                _record_issue(
                    "Most recent sanitation check did not pass",
                    "Schedule a follow-up sanitation inspection and upload the results.",
                    document_gap=False,
                )
            if latest_log.get("follow_up_required"):
                recommendations.append(
                    "Resolve outstanding sanitation follow-up items and document completion."
                )
        else:
            _record_issue(
                "Sanitation logs missing",
                "Record a sanitation checklist entry for this kitchen.",
                document_gap=True,
            )

        risk_score = max(0, 100 - 15 * len(missing_requirements))

        if not kitchen_data.get("state"):
            _record_issue(
                "Kitchen location missing state metadata",
                None,
                document_gap=True,
            )
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
                ComplianceLevel.COMPLIANT if kitchen_data.get("state") else ComplianceLevel.UNKNOWN
            )

        return ComplianceAnalysis(
            overall_compliance=overall,
            risk_score=risk_score,
            missing_requirements=missing_requirements,
            recommendations=recommendations,
            last_analyzed=datetime.now(UTC),
            kitchen_id=str(kitchen_data.get("id", "unknown")),
            state=kitchen_data.get("state"),
            city=kitchen_data.get("city"),
            metadata={
                **metadata,
                "pilot_mode": pilot_mode,
                "pilot_warnings": warnings,
            },
        )


__all__ = ["ComplianceAnalysis", "ComplianceLevel", "RegulatoryAnalyzer"]
