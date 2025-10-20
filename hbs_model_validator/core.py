import json
from pathlib import Path
from __future__ import annotations

import json
from typing import Any, Dict, List


class HBSModelValidator:
    """Validates HBS models for consistency and compliance."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] | None = None
        self.last_errors: List[str] = []
        self.validated: bool = False

    def load_config(self, config_path: str) -> None:
        """Load validation configuration from the specified path."""
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)

        required_fields = config.get("required_fields")
        if not isinstance(required_fields, list) or not all(
            isinstance(field, str) for field in required_fields
        ):
            raise ValueError("required_fields missing or invalid")

        value_range = config.get("value_range", {})
        if not isinstance(value_range, dict):
            raise ValueError("value_range must be a dict")

        for field, bounds in value_range.items():
            if (
                not isinstance(bounds, list)
                or len(bounds) != 2
                or not all(isinstance(x, (int, float)) for x in bounds)
            ):
                raise ValueError(f"Invalid range for {field}")

        self.config = config

    def validate(self, model: Dict[str, Any]) -> bool:
        """Run validation routines on the provided model."""
        if self.config is None:
            raise ValueError("Configuration not loaded")

        self.last_errors = []
        required_fields = self.config.get("required_fields", [])
        for field in required_fields:
            if field not in model:
                self.last_errors.append(f"Missing field: {field}")

        value_range = self.config.get("value_range", {})
        for field, bounds in value_range.items():
            if field in model:
                min_val, max_val = bounds
                value = model[field]
                if (
                    not isinstance(value, (int, float))
                    or value < min_val
                    or value > max_val
                ):
                    self.last_errors.append(
                        f"{field}={value} out of range {min_val}-{max_val}"
                    )

        self.validated = not self.last_errors
        return self.validated

    def generate_report(self) -> str:
        """Create a report summarizing validation results."""
        if self.config is None:
            raise ValueError("Configuration not loaded")

        if not self.last_errors and not self.validated:
            return "No validation performed"

        status = "passed" if self.validated else "failed"
        report = f"Validation {status}."
        if self.last_errors:
            report += "\nErrors:\n" + "\n".join(self.last_errors)
        return report
        self.schema: Dict[str, str] = {}
        self.required_fields: List[str] = []
        self.errors: List[str] = []

    def load_config(self, config_path: str) -> None:
        """Load validation configuration from the specified path.

        The configuration is expected to be a JSON file with two keys:
        ``schema`` mapping field names to expected types and ``required``
        listing fields that must be present.
        """

        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        self.schema = config.get("schema", {})
        self.required_fields = config.get("required", [])

    def validate(self, model: Dict[str, Any]) -> bool:
        """Run validation routines on the provided model.

        The model is expected to be a mapping. Required fields and type
        checks are performed according to the previously loaded schema.
        Returns ``True`` if no validation errors were found, otherwise
        ``False``.
        """

        self.errors = []

        # Check for required fields
        for field in self.required_fields:
            if field not in model:
                self.errors.append(f"Missing required field: {field}")

        # Type validation
        type_map = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }

        for field, expected_type in self.schema.items():
            if field in model and expected_type in type_map:
                if not isinstance(model[field], type_map[expected_type]):
                    self.errors.append(
                        f"Field '{field}' expected type {expected_type}, got {type(model[field]).__name__}"
                    )

        return not self.errors

    def generate_report(self) -> str:
        """Create a report summarizing validation results."""

        if not self.errors:
            return "Validation passed with 0 errors."

        error_lines = "\n".join(f"- {msg}" for msg in self.errors)
        return f"Validation failed with errors:\n{error_lines}"
