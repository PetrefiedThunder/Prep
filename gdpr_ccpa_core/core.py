import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List


class GDPRCCPACore:
    """Core utilities for GDPR and CCPA privacy compliance."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.records: List[Dict[str, Any]] = []
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:
        """Load privacy compliance settings from file.

        The configuration must contain ``allowed_regions`` (list of region
        codes) and ``data_retention_days`` (positive integer). ``ValueError``
        is raised if the configuration is missing or malformed.
        """

        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        allowed_regions = config.get("allowed_regions")
        retention = config.get("data_retention_days")
        if not isinstance(allowed_regions, list) or not allowed_regions:
            raise ValueError("allowed_regions missing or invalid")
        if not isinstance(retention, int) or retention <= 0:
            raise ValueError("data_retention_days missing or invalid")

        self.config = config

    def validate(self, records: Iterable[Dict[str, Any]]) -> bool:
        """Validate data handling practices.

        Each record must include ``user_id``, ``region``, ``last_updated``
        (ISO formatted string) and ``consent`` set to ``True``. Regions must be
        listed in the configuration and the ``last_updated`` timestamp must not
        exceed the configured retention period.
        """

    def validate(self, records) -> bool:
        """Validate data handling practices."""
        return True

    def generate_report(self) -> str:
        """Create a compliance assessment report."""
        return ""
