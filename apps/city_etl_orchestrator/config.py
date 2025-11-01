"""Configuration helpers for the City ETL orchestrator service."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_INTERVAL_SECONDS = 3600
DEFAULT_FRESHNESS_SLO_SECONDS = 7200


@dataclass(frozen=True)
class OrchestratorSettings:
    """Runtime configuration derived from environment variables."""

    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    freshness_slo_seconds: int = DEFAULT_FRESHNESS_SLO_SECONDS


def load_settings() -> OrchestratorSettings:
    """Load orchestrator settings from environment variables."""

    interval = int(os.getenv("CITY_ETL_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))
    freshness = int(
        os.getenv("CITY_ETL_FRESHNESS_SLO_SECONDS", DEFAULT_FRESHNESS_SLO_SECONDS)
    )
    return OrchestratorSettings(interval_seconds=interval, freshness_slo_seconds=freshness)
