"""Core Department of Labor compliance validation engine."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from prep.utility.config_schema import BaseConfigSchema, IterableValidationMixin


class DOLRegComplianceEngine(IterableValidationMixin, BaseConfigSchema):
    """Ensures Department of Labor regulation compliance."""

    def __init__(self, *, logger=None) -> None:
        super().__init__(logger=logger)
        self.records: list[dict[str, Any]] = []
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:  # type: ignore[override]
        super().load_config(config_path)
        min_wage = self.config.get("minimum_wage")
        max_hours = self.config.get("max_hours_per_week")
        if not isinstance(min_wage, (int, float)) or float(min_wage) <= 0:
            raise ValueError("minimum_wage missing or invalid")
        if not isinstance(max_hours, int) or int(max_hours) <= 0:
            raise ValueError("max_hours_per_week missing or invalid")

    def validate(self, data: Iterable[dict[str, Any]]) -> bool:  # type: ignore[override]
        return super().validate(data)

    def _run_validation(self, data: Iterable[dict[str, Any]]) -> list[str]:  # type: ignore[override]
        records_list = self._ensure_list(data)
        errors: list[str] = []
        min_wage = float(self.config["minimum_wage"])
        max_hours = int(self.config["max_hours_per_week"])

        for index, record in enumerate(records_list):
            wage = record.get("wage")
            hours = record.get("hours_worked")

            if wage is None:
                errors.append(f"Record {index} missing wage")
            elif float(wage) < min_wage:
                errors.append(f"Record {index} wage {wage} below minimum wage {min_wage}")

            if hours is None:
                errors.append(f"Record {index} missing hours_worked")
            elif int(hours) > max_hours:
                errors.append(f"Record {index} hours {hours} exceed max {max_hours}")

        self.records = records_list
        self.is_valid = not errors
        return errors

    def generate_report(self) -> str:  # type: ignore[override]
        """Generate a compliance report."""
        if not self.records and not self.validation_errors and not self._validated:
            raise ValueError("No records validated")

        if not self._validated and not self.validation_errors:
            raise ValueError("Validation has not been run")

        summary = f"Records checked: {len(self.records)}, Compliant: {self.is_valid}"

        if self.validation_errors:
            errors = "\n".join(self.validation_errors)
            return f"{summary}\nErrors:\n{errors}"

        return summary
