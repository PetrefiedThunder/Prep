from __future__ import annotations

import json
from typing import Any, Dict, List


class HBSModelValidator:
    """Validates HBS models for consistency and compliance."""

    def __init__(self) -> None:
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
