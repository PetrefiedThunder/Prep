from __future__ import annotations

"""Schema validation and sanitisation helpers for compliance engines."""

from datetime import datetime
import re
from typing import Any, Dict, List, Mapping, Sequence


class DataValidator:
    """Utilities for validating and sanitizing compliance data."""

    @staticmethod
    def validate_kitchen_data(data: Dict[str, Any]) -> List[str]:
        """Validate critical fields for kitchen compliance data."""

        errors: List[str] = []

        def _expect_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
            if value in (None, ""):
                return {}
            if not isinstance(value, Mapping):
                errors.append(f"{field_name} must be an object")
                return {}
            return value

        def _expect_sequence(value: Any, field_name: str) -> Sequence[Any]:
            if value in (None, ""):
                return []
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
                errors.append(f"{field_name} must be an array")
                return []
            return value

        license_info = _expect_mapping(data.get("license_info"), "license_info")
        if license_info:
            if not license_info.get("license_number"):
                errors.append("license_info.license_number is required")
            if not license_info.get("status"):
                errors.append("license_info.status is required")
            expiration = license_info.get("expiration_date")
            if expiration and not DataValidator.validate_date_string(str(expiration)):
                errors.append("license_info.expiration_date must be an ISO-8601 date")

        inspection_history = _expect_sequence(
            data.get("inspection_history"), "inspection_history"
        )
        for index, inspection in enumerate(inspection_history, start=1):
            if not isinstance(inspection, Mapping):
                errors.append(f"inspection_history[{index}]: entry must be an object")
                continue
            inspection_date = inspection.get("inspection_date")
            if not inspection_date:
                errors.append(f"inspection_history[{index}].inspection_date is required")
            elif not DataValidator.validate_date_string(str(inspection_date)):
                errors.append(
                    f"inspection_history[{index}].inspection_date must be an ISO-8601 date"
                )
            if inspection.get("overall_score") is None:
                errors.append(f"inspection_history[{index}].overall_score is required")
            if "violations" not in inspection:
                errors.append(f"inspection_history[{index}].violations is required")
            if "establishment_closed" not in inspection:
                errors.append(
                    f"inspection_history[{index}].establishment_closed is required"
                )

        certifications = _expect_sequence(data.get("certifications"), "certifications")
        for index, certification in enumerate(certifications, start=1):
            if not isinstance(certification, Mapping):
                errors.append(f"certifications[{index}] must be an object")
                continue
            if not certification.get("type"):
                errors.append(f"certifications[{index}].type is required")
            if not certification.get("status"):
                errors.append(f"certifications[{index}].status is required")

        equipment = _expect_sequence(data.get("equipment"), "equipment")
        for index, item in enumerate(equipment, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"equipment[{index}] must be an object")
                continue
            if not item.get("type"):
                errors.append(f"equipment[{index}].type is required")
            if "commercial_grade" not in item:
                errors.append(f"equipment[{index}].commercial_grade is required")
            if "nsf_certified" not in item:
                errors.append(f"equipment[{index}].nsf_certified is required")

        insurance = _expect_mapping(data.get("insurance"), "insurance")
        if insurance:
            if not insurance.get("policy_number"):
                errors.append("insurance.policy_number is required")
            expiration = insurance.get("expiration_date")
            if expiration and not DataValidator.validate_date_string(str(expiration)):
                errors.append("insurance.expiration_date must be an ISO-8601 date")

        pest_control_records = _expect_sequence(
            data.get("pest_control_records"), "pest_control_records"
        )
        for index, record in enumerate(pest_control_records, start=1):
            if not isinstance(record, Mapping):
                errors.append(f"pest_control_records[{index}] must be an object")
                continue
            service_date = record.get("service_date")
            if service_date and not DataValidator.validate_date_string(str(service_date)):
                errors.append(
                    f"pest_control_records[{index}].service_date must be an ISO-8601 date"
                )

        cleaning_logs = _expect_sequence(data.get("cleaning_logs"), "cleaning_logs")
        for index, log in enumerate(cleaning_logs, start=1):
            if not isinstance(log, Mapping):
                errors.append(f"cleaning_logs[{index}] must be an object")
                continue
            date_value = log.get("date")
            if date_value and not DataValidator.validate_date_string(str(date_value)):
                errors.append(
                    f"cleaning_logs[{index}].date must be an ISO-8601 date"
                )

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
