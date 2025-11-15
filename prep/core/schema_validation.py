"""JSON Schema validation utilities for compliance engine outputs."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .orchestration import ComplianceDomain


class SchemaValidationError(ValueError):
    """Raised when a compliance engine output fails schema validation."""

    def __init__(self, domain: ComplianceDomain, errors: Iterable[str]) -> None:
        self.domain = domain
        self.errors = list(errors)
        message = "; ".join(self.errors) if self.errors else "Schema validation failed"
        super().__init__(f"{domain.value} validation failed: {message}")


class SchemaValidator:
    """Validate compliance engine outputs against published schemas."""

    def __init__(self, base_path: Path | None = None) -> None:
        root = (base_path or Path(__file__).resolve().parents[2]).resolve()
        self._schemas: dict[ComplianceDomain, dict[str, Any]] = {}
        schema_map = {
            ComplianceDomain.GDPR_CCPA: root / "schemas/privacy/compliance_result.schema.json",
            ComplianceDomain.AML_KYC: root / "schemas/aml/compliance_result.schema.json",
        }
        for domain, path in schema_map.items():
            if path.exists():
                with path.open("r", encoding="utf-8") as handle:
                    self._schemas[domain] = json.load(handle)

    def ensure_valid(self, domain: ComplianceDomain, payload: Any) -> Mapping[str, Any]:
        """Normalize payload and raise ``SchemaValidationError`` if invalid."""

        normalized = self._normalize_payload(domain, payload)
        schema = self._schemas.get(domain)
        if schema is None:
            return normalized

        errors: list[str] = []
        self._validate(schema, normalized, errors, path=())
        if errors:
            raise SchemaValidationError(domain, errors)
        return normalized

    def _normalize_payload(
        self, domain: ComplianceDomain, payload: Any
    ) -> MutableMapping[str, Any]:
        if is_dataclass(payload):
            data: MutableMapping[str, Any] = asdict(payload)  # type: ignore[assignment]
        elif isinstance(payload, Mapping):
            data = dict(payload)
        else:
            raise TypeError(f"Unsupported payload type for domain {domain}: {type(payload)!r}")

        data.setdefault("domain", domain.value)
        if "schema_version" in data and "x-schema-version" not in data:
            data["x-schema-version"] = data.pop("schema_version")
        return data

    def _validate(
        self,
        schema: Mapping[str, Any],
        value: Any,
        errors: list[str],
        *,
        path: Sequence[str | int],
    ) -> None:
        schema_type = schema.get("type")
        if schema_type == "object":
            if not isinstance(value, Mapping):
                errors.append(self._format_error(path, "must be an object"))
                return
            required = schema.get("required", [])
            for key in required:
                if key not in value:
                    errors.append(self._format_error(path + (key,), "is a required property"))
            properties: Mapping[str, Any] = schema.get("properties", {})
            if schema.get("additionalProperties") is False:
                allowed = set(properties.keys())
                for key in value:
                    if key not in allowed:
                        errors.append(self._format_error(path + (str(key),), "is not allowed"))
            for key, subschema in properties.items():
                if key in value:
                    self._validate(subschema, value[key], errors, path=path + (key,))
        elif schema_type == "array":
            if not isinstance(value, list):
                errors.append(self._format_error(path, "must be an array"))
                return
            min_items = schema.get("minItems")
            if isinstance(min_items, int) and len(value) < min_items:
                errors.append(self._format_error(path, f"must contain at least {min_items} items"))
            item_schema = schema.get("items")
            if isinstance(item_schema, Mapping):
                for index, item in enumerate(value):
                    self._validate(item_schema, item, errors, path=path + (index,))
        elif schema_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(self._format_error(path, "must be a number"))
                return
            minimum = schema.get("minimum")
            if minimum is not None and value < minimum:
                errors.append(self._format_error(path, f"must be >= {minimum}"))
            maximum = schema.get("maximum")
            if maximum is not None and value > maximum:
                errors.append(self._format_error(path, f"must be <= {maximum}"))
        elif schema_type == "string":
            if not isinstance(value, str):
                errors.append(self._format_error(path, "must be a string"))
                return
            min_length = schema.get("minLength")
            if isinstance(min_length, int) and len(value) < min_length:
                errors.append(
                    self._format_error(path, f"must be at least {min_length} characters long")
                )
        elif schema_type == "boolean":
            if not isinstance(value, bool):
                errors.append(self._format_error(path, "must be a boolean"))

        if "const" in schema and value != schema["const"]:
            errors.append(self._format_error(path, f"must equal {schema['const']!r}"))
        enum = schema.get("enum")
        if enum is not None and value not in enum:
            errors.append(self._format_error(path, f"must be one of {enum!r}"))

    def _format_error(self, path: Sequence[str | int], message: str) -> str:
        if not path:
            return message
        formatted = ".".join(str(p) for p in path)
        return f"{formatted} {message}"


__all__ = ["SchemaValidator", "SchemaValidationError"]
