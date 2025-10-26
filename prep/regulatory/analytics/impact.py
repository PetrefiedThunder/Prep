"""Impact assessment utilities for regulatory intelligence dashboards."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class ImpactDataSource(Protocol):
    """Interface for retrieving data required for impact analysis."""

    async def find_affected_kitchens(self, regulation_change: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...


class RegulatoryImpactAssessor:
    """Assess business impact for regulatory updates."""

    def __init__(self, data_source: Optional[ImpactDataSource] = None) -> None:
        self.data_source = data_source

    async def assess_impact(self, regulation_change: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured impact report for a regulation change."""

        kitchens = await self.find_affected_kitchens(regulation_change)
        total_affected = len(kitchens)
        return {
            "total_affected": total_affected,
            "compliance_cost_estimate": self.estimate_compliance_cost(regulation_change, total_affected),
            "timeline_impact": self.estimate_timeline_impact(regulation_change),
            "risk_assessment": self.associate_risks(regulation_change, kitchens),
        }

    async def find_affected_kitchens(self, regulation_change: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.data_source:
            return await self.data_source.find_affected_kitchens(regulation_change)
        logger.debug("Using fallback affected kitchen detection.")
        jurisdiction = regulation_change.get("jurisdiction")
        return [
            {"id": "demo-1", "jurisdiction": jurisdiction, "size": "large"},
            {"id": "demo-2", "jurisdiction": jurisdiction, "size": "small"},
        ]

    def estimate_compliance_cost(self, regulation_change: Dict[str, Any], total_affected: int) -> float:
        base_cost = float(regulation_change.get("estimated_cost", 1500))
        complexity_factor = 1.5 if regulation_change.get("type") == "health" else 1.2
        return round(base_cost * complexity_factor * max(total_affected, 1), 2)

    def estimate_timeline_impact(self, regulation_change: Dict[str, Any]) -> Dict[str, Any]:
        timeframe = regulation_change.get("implementation_deadline", "90 days")
        severity = "high" if "immediate" in str(timeframe).lower() else "medium"
        return {"implementation_window": timeframe, "urgency": severity}

    def associate_risks(self, regulation_change: Dict[str, Any], kitchens: List[Dict[str, Any]]) -> List[str]:
        risks: List[str] = []
        if regulation_change.get("requires_new_equipment"):
            risks.append("Capital expenditure for new equipment")
        if any(kitchen.get("size") == "small" for kitchen in kitchens):
            risks.append("Potential capacity constraints for small operators")
        if regulation_change.get("type") == "insurance":
            risks.append("Insurance policy renegotiation required")
        return risks


__all__ = ["RegulatoryImpactAssessor", "ImpactDataSource"]
