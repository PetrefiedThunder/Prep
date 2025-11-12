from __future__ import annotations

"""Schema validation and sanitisation helpers for compliance engines."""

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any


class DataValidator:
    """Utilities for validating and sanitizing compliance data."""

    @staticmethod
    def validate_kitchen_data(data: dict[str, Any]) -> list[str]:
        """Validate critical fields for kitchen compliance data."""

        errors: list[str] = []

        acronyms = {"id": "ID", "nsf": "NSF", "fips": "FIPS"}

        def _titleize(identifier: str) -> str:
            parts = re.split(r"[_\s]+", identifier.strip())
            words = []
            for part in parts:
                if not part:
                    continue
                lower = part.lower()
                if lower in acronyms:
                    words.append(acronyms[lower])
                else:
                    words.append(part.capitalize())
            return " ".join(words)

        def _section_label(
            name: str, index: int | None = None, *, custom: str | None = None
        ) -> str:
            label = _titleize(custom or name)
            if index is not None:
                label = f"{label} {index}"
            return label

        def _message(
            name: str, message: str, index: int | None = None, *, custom: str | None = None
        ) -> None:
            errors.append(f"{_section_label(name, index, custom=custom)}: {message}.")

        def _field_required(
            name: str, field: str, index: int | None = None, *, custom: str | None = None
        ) -> None:
            _message(name, f"{_titleize(field)} is required", index, custom=custom)

        def _invalid_date(
            name: str, field: str, index: int | None = None, *, custom: str | None = None
        ) -> None:
            _message(
                name,
                f"{_titleize(field)} has an invalid date format (expected ISO-8601)",
                index,
                custom=custom,
            )

        def _expected_type(name: str, expected: str, *, custom: str | None = None) -> None:
            _message(name, f"Expected {expected}", custom=custom)

        def _expected_entry_type(
            name: str,
            expected: str,
            index: int,
            *,
            custom: str | None = None,
        ) -> None:
            _message(name, f"Expected {expected}", index, custom=custom)

        def _expect_mapping(
            value: Any, field_name: str, *, label: str | None = None
        ) -> Mapping[str, Any]:
            if value in (None, ""):
                return {}
            if not isinstance(value, Mapping):
                _expected_type(field_name, "an object", custom=label)
                return {}
            return value

        def _expect_sequence(
            value: Any,
            field_name: str,
            *,
            label: str | None = None,
        ) -> Sequence[Any]:
            if value in (None, ""):
                return []
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
                _expected_type(field_name, "an array", custom=label)
                return []
            return value

        license_info = _expect_mapping(
            data.get("license_info"), "license_info", label="License Info"
        )
        if license_info:
            if not license_info.get("license_number"):
                _field_required("license_info", "license_number", custom="License Info")
            if not license_info.get("status"):
                _field_required("license_info", "status", custom="License Info")
            expiration = license_info.get("expiration_date")
            if expiration and not DataValidator.validate_date_string(str(expiration)):
                _invalid_date("license_info", "expiration_date", custom="License Info")

        inspection_history = _expect_sequence(
            data.get("inspection_history"), "inspection_history", label="Inspection History"
        )
        for index, inspection in enumerate(inspection_history, start=1):
            if not isinstance(inspection, Mapping):
                _expected_entry_type("inspection_history", "an object", index, custom="Inspection")
                continue
            inspection_date = inspection.get("inspection_date")
            if not inspection_date:
                _field_required(
                    "inspection_history",
                    "inspection_date",
                    index,
                    custom="Inspection",
                )
            elif not DataValidator.validate_date_string(str(inspection_date)):
                _invalid_date(
                    "inspection_history",
                    "inspection_date",
                    index,
                    custom="Inspection",
                )
            if inspection.get("overall_score") is None:
                _field_required("inspection_history", "overall_score", index, custom="Inspection")
            if "violations" not in inspection:
                _field_required("inspection_history", "violations", index, custom="Inspection")
            if "establishment_closed" not in inspection:
                _field_required(
                    "inspection_history",
                    "establishment_closed",
                    index,
                    custom="Inspection",
                )

        certifications = _expect_sequence(
            data.get("certifications"), "certifications", label="Certifications"
        )
        for index, certification in enumerate(certifications, start=1):
            if not isinstance(certification, Mapping):
                _expected_entry_type("certifications", "an object", index, custom="Certification")
                continue
            if not certification.get("type"):
                _field_required("certifications", "type", index, custom="Certification")
            if not certification.get("status"):
                _field_required("certifications", "status", index, custom="Certification")

        equipment = _expect_sequence(data.get("equipment"), "equipment", label="Equipment")
        for index, item in enumerate(equipment, start=1):
            if not isinstance(item, Mapping):
                _expected_entry_type("equipment", "an object", index, custom="Equipment")
                continue
            if not item.get("type"):
                _field_required("equipment", "type", index, custom="Equipment")
            if "commercial_grade" not in item:
                _field_required("equipment", "commercial_grade", index, custom="Equipment")
            if "nsf_certified" not in item:
                _field_required("equipment", "nsf_certified", index, custom="Equipment")

        recipes = _expect_sequence(data.get("recipes"), "recipes", label="Recipes")
        for recipe_index, recipe in enumerate(recipes, start=1):
            if not isinstance(recipe, Mapping):
                _expected_entry_type("recipes", "an object", recipe_index, custom="Recipe")
                continue
            if not recipe.get("name"):
                _field_required("recipes", "name", recipe_index, custom="Recipe")
            allergens = recipe.get("allergens")
            if allergens in (None, ""):
                continue
            if not isinstance(allergens, Sequence) or isinstance(
                allergens, (str, bytes, bytearray)
            ):
                _expected_type("recipes", "an array", custom="Recipe Allergens")
                continue
            for allergen_index, allergen in enumerate(allergens, start=1):
                label = f"Recipe {recipe_index} Allergen"
                if not isinstance(allergen, Mapping):
                    _expected_entry_type("recipes", "an object", allergen_index, custom=label)
                    continue
                if not allergen.get("name"):
                    _field_required("recipes", "name", allergen_index, custom=label)
                if "present" not in allergen:
                    _field_required("recipes", "present", allergen_index, custom=label)
                if "declared" not in allergen:
                    _field_required("recipes", "declared", allergen_index, custom=label)

        allergen_summary = data.get("allergens_summary")
        if allergen_summary not in (None, {}):
            if not isinstance(allergen_summary, Mapping):
                _expected_type("allergens_summary", "an object")
            else:
                for name, entry in allergen_summary.items():
                    if not isinstance(entry, Mapping):
                        _expected_type("allergens_summary", "an object", custom=f"Allergen {name}")
                        continue
                    if "recipes" not in entry:
                        _message(
                            "allergens_summary",
                            "Recipes count is required",
                            custom=f"Allergen {name}",
                        )
                    if "undeclared" not in entry:
                        _message(
                            "allergens_summary",
                            "Undeclared count is required",
                            custom=f"Allergen {name}",
                        )

        insurance = _expect_mapping(data.get("insurance"), "insurance", label="Insurance")
        if insurance:
            if not insurance.get("policy_number"):
                _field_required("insurance", "policy_number", custom="Insurance")
            expiration = insurance.get("expiration_date")
            if expiration and not DataValidator.validate_date_string(str(expiration)):
                _invalid_date("insurance", "expiration_date", custom="Insurance")

        pest_control_records = _expect_sequence(
            data.get("pest_control_records"),
            "pest_control_records",
            label="Pest Control Records",
        )
        for index, record in enumerate(pest_control_records, start=1):
            if not isinstance(record, Mapping):
                _expected_entry_type(
                    "pest_control_records",
                    "an object",
                    index,
                    custom="Pest Control Record",
                )
                continue
            service_date = record.get("service_date")
            if service_date and not DataValidator.validate_date_string(str(service_date)):
                _invalid_date(
                    "pest_control_records",
                    "service_date",
                    index,
                    custom="Pest Control Record",
                )

        cleaning_logs = _expect_sequence(
            data.get("cleaning_logs"), "cleaning_logs", label="Cleaning Logs"
        )
        for index, log in enumerate(cleaning_logs, start=1):
            if not isinstance(log, Mapping):
                _expected_entry_type("cleaning_logs", "an object", index, custom="Cleaning Log")
                continue
            date_value = log.get("date")
            if date_value and not DataValidator.validate_date_string(str(date_value)):
                _invalid_date("cleaning_logs", "date", index, custom="Cleaning Log")

        return sorted(set(errors))

    @staticmethod
    def validate_date_string(date_str: str) -> bool:
        """Return True if the string is a valid ISO-8601 datetime."""

        try:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return False
        return True

    @staticmethod
    def sanitize_kitchen_data(data: dict[str, Any]) -> dict[str, Any]:
        """Return a sanitized copy of the provided kitchen data."""

        sanitized: dict[str, Any] = {}
        allowed_fields = {
            "license_info",
            "inspection_history",
            "certifications",
            "equipment",
            "insurance",
            "photos",
            "pest_control_records",
            "cleaning_logs",
            "recipes",
            "allergens_summary",
            "license_number",
            "county_fips",
        }

        for key, value in data.items():
            if key in allowed_fields:
                sanitized[key] = DataValidator._sanitize_value(value)

        return sanitized

    @staticmethod
    def _sanitize_value(value: Any) -> Any:
        """Recursively sanitize values to reduce injection risk."""

        if isinstance(value, str):
            return re.sub(r"[<>\"']", "", value)
        if isinstance(value, list):
            return [DataValidator._sanitize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: DataValidator._sanitize_value(val) for key, val in value.items()}
        return value
