from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from prep.utility.config_schema import BaseConfigSchema


class HBSModelValidator(BaseConfigSchema):
    """Validates HBS models for consistency and compliance."""

    _TYPE_MAP = {
        "string": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    def __init__(self, *, logger=None) -> None:
        super().__init__(logger=logger)
        self.last_errors: List[str] = []
        self.validated: bool = False

    def load_config(self, config_path: str) -> None:  # type: ignore[override]
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)

        required_fields = config.get("required_fields", config.get("required", []))
        if not isinstance(required_fields, list) or not all(
            isinstance(field, str) for field in required_fields
        ):
            raise ValueError("required_fields missing or invalid")

        value_range = config.get("value_range", {})
        if not isinstance(value_range, dict):
            raise ValueError("value_range must be a dict")
        normalised_ranges: Dict[str, List[float]] = {}
        for field, bounds in value_range.items():
            if (
                not isinstance(bounds, (list, tuple))
                or len(bounds) != 2
                or not all(isinstance(x, (int, float)) for x in bounds)
            ):
                raise ValueError(f"Invalid range for {field}")
            normalised_ranges[field] = [float(bounds[0]), float(bounds[1])]

        schema = config.get("schema", {})
        if not isinstance(schema, dict):
            raise ValueError("schema must be a dict")
        for field, type_name in schema.items():
            if type_name not in self._TYPE_MAP:
                raise ValueError(f"Unsupported type for {field}: {type_name}")

        self.config = {
            "required_fields": required_fields,
            "value_range": normalised_ranges,
            "schema": schema,
        }
        self.last_errors = []
        self.validated = False

    def validate(self, model: Dict[str, Any]) -> bool:  # type: ignore[override]
        return super().validate(model)

    def _run_validation(self, model: Dict[str, Any]) -> List[str]:  # type: ignore[override]
        if not isinstance(model, dict):
            return ["Model must be a mapping"]

        errors: List[str] = []

        for field in self.config.get("required_fields", []):
            if field not in model:
                errors.append(f"Missing field: {field}")

        schema = self.config.get("schema", {})
        for field, type_name in schema.items():
            if field in model:
                expected_type = self._TYPE_MAP[type_name]
                if not isinstance(model[field], expected_type):
                    errors.append(
                        f"Field '{field}' expected type {type_name}, "
                        f"got {type(model[field]).__name__}"
                    )

        value_range = self.config.get("value_range", {})
        for field, (min_val, max_val) in value_range.items():
            if field in model:
                value = model[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be numeric for range validation")
                elif value < min_val or value > max_val:
                    errors.append(
                        f"{field}={value} out of range {min_val}-{max_val}"
                    )

        self.last_errors = errors
        self.validated = not errors
        return errors

    def generate_report(self) -> str:  # type: ignore[override]
        if not self._validated and not self.last_errors:
            raise ValueError("Validation has not been run")

        status = "passed" if self.validated else "failed"
        report = f"Validation {status}."
        if self.last_errors:
            report += "\nErrors:\n" + "\n".join(self.last_errors)
        return report
