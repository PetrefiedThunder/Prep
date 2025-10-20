from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List


class DataValidator:
    """Utilities for validating and sanitizing compliance data."""

    @staticmethod
    def validate_kitchen_data(data: Dict[str, Any]) -> List[str]:
        """Validate critical fields for kitchen compliance data."""

        errors: List[str] = []

        license_info = data.get("license_info", {}) or {}
        if license_info:
            if not license_info.get("license_number"):
                errors.append("License number is required")
            if not license_info.get("status"):
                errors.append("License status is required")

        inspection_history = data.get("inspection_history", []) or []
        for index, inspection in enumerate(inspection_history, start=1):
            inspection_date = inspection.get("inspection_date")
            if not inspection_date:
                errors.append(f"Inspection {index}: Inspection date is required")
                continue
            if isinstance(inspection_date, str):
                try:
                    datetime.fromisoformat(inspection_date.replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    errors.append(f"Inspection {index}: Invalid date format")

        equipment = data.get("equipment", []) or []
        for index, item in enumerate(equipment, start=1):
            if not item.get("type"):
                errors.append(f"Equipment {index}: Type is required")

        return errors

    @staticmethod
    def validate_date_string(date_str: str) -> bool:
        """Return True if the string is a valid ISO-8601 datetime."""

        try:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return False
        return True

    @staticmethod
    def sanitize_kitchen_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a sanitized copy of the provided kitchen data."""

        sanitized: Dict[str, Any] = {}
        allowed_fields = {
            "license_info",
            "inspection_history",
            "certifications",
            "equipment",
            "insurance",
            "photos",
            "pest_control_records",
            "cleaning_logs",
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
