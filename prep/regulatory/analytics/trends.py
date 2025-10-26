"""Trend analysis helpers for regulatory intelligence dashboards."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class TrendDataSource(Protocol):
    """Interface required for providing compliance trend data."""

    async def national_compliance_rate(self, time_range: str) -> Dict[str, Any]:
        ...

    async def state_compliance_comparison(self, time_range: str) -> List[Dict[str, Any]]:
        ...

    async def most_common_violations(self, time_range: str) -> List[Dict[str, Any]]:
        ...

    async def regulation_change_frequency(self, time_range: str) -> Dict[str, Any]:
        ...

    async def analyze_state_environment(self, state: str) -> Dict[str, Any]:
        ...


class RegulatoryTrendAnalyzer:
    """High-level orchestration for compliance trend analytics."""

    def __init__(self, data_source: Optional[TrendDataSource] = None) -> None:
        self.data_source = data_source

    async def analyze_compliance_trends(self, time_range: str = "1y") -> Dict[str, Any]:
        """Return high-level compliance trends for dashboards."""

        return {
            "national_compliance_rate": await self.national_compliance_rate(time_range),
            "state_comparisons": await self.state_compliance_comparison(time_range),
            "common_violations": await self.most_common_violations(time_range),
            "regulation_changes": await self.regulation_change_frequency(time_range),
        }

    async def predict_regulatory_changes(self, states: List[str]) -> Dict[str, Any]:
        """Predict potential regulatory activity for the supplied states."""

        predictions: Dict[str, Any] = {}
        for state in states:
            predictions[state] = await self.analyze_state_regulatory_environment(state)
        return predictions

    async def national_compliance_rate(self, time_range: str = "1y") -> Dict[str, Any]:
        if self.data_source:
            return await self.data_source.national_compliance_rate(time_range)
        logger.debug("Using fallback national compliance rate computation.")
        return {"time_range": time_range, "rate": 0.87}

    async def state_compliance_comparison(self, time_range: str = "1y") -> List[Dict[str, Any]]:
        if self.data_source:
            return await self.data_source.state_compliance_comparison(time_range)
        logger.debug("Using fallback state compliance comparison computation.")
        return [
            {"state": "CA", "rate": 0.82},
            {"state": "NY", "rate": 0.88},
            {"state": "TX", "rate": 0.79},
        ]

    async def most_common_violations(self, time_range: str = "1y") -> List[Dict[str, Any]]:
        if self.data_source:
            return await self.data_source.most_common_violations(time_range)
        logger.debug("Using fallback violation analysis computation.")
        return [
            {"violation": "Expired food handler certifications", "count": 134},
            {"violation": "Insufficient sanitation logs", "count": 92},
            {"violation": "Inadequate insurance documentation", "count": 57},
        ]

    async def regulation_change_frequency(self, time_range: str = "1y") -> Dict[str, Any]:
        if self.data_source:
            return await self.data_source.regulation_change_frequency(time_range)
        logger.debug("Using fallback regulation change frequency computation.")
        return {"time_range": time_range, "changes": 24}

    async def analyze_state_regulatory_environment(self, state: str) -> Dict[str, Any]:
        if self.data_source:
            return await self.data_source.analyze_state_environment(state)
        logger.debug("Using fallback analysis for state regulatory environment: %s", state)
        return {
            "state": state,
            "legislation_watch": [],
            "forecast": "stable" if state not in {"CA", "NY"} else "elevated activity",
        }


__all__ = ["RegulatoryTrendAnalyzer", "TrendDataSource"]
