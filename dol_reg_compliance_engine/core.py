import json
from typing import Any, Dict, Iterable, List


class DOLRegComplianceEngine:
    """Ensures Department of Labor regulation compliance."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.records: List[Dict[str, Any]] = []
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:
        """Load compliance rules from configuration.

        Expected keys are ``minimum_wage`` (float) and ``max_hours_per_week``
        (int). ``ValueError`` is raised for missing or malformed
        configuration values.
        """

        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        min_wage = config.get("minimum_wage")
        max_hours = config.get("max_hours_per_week")
        if not isinstance(min_wage, (int, float)) or min_wage <= 0:
            raise ValueError("minimum_wage missing or invalid")
        if not isinstance(max_hours, int) or max_hours <= 0:
            raise ValueError("max_hours_per_week missing or invalid")

        self.config = config

    def validate(self, data: Iterable[Dict[str, Any]]) -> bool:
        """Validate input data against DOL regulations."""

        if not self.config:
            raise ValueError("Configuration not loaded")

        data_list = list(data)

        min_wage = float(self.config["minimum_wage"])
        max_hours = int(self.config["max_hours_per_week"])

        for record in data_list:
            wage = record.get("wage")
            hours = record.get("hours_worked")
            if wage is None or float(wage) < min_wage:
                self.is_valid = False
                return False
            if hours is None or int(hours) > max_hours:
                self.is_valid = False
                return False

        self.records = data_list
        self.is_valid = True
        return True

    def generate_report(self) -> str:
        """Generate a compliance report."""
        if not self.records:
            raise ValueError("No records validated")

        return (
            f"Records checked: {len(self.records)}, "
            f"Compliant: {self.is_valid}"
        )
