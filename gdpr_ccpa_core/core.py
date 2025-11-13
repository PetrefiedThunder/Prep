import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any


class GDPRCCPACore:
    """Core utilities for GDPR and CCPA privacy compliance."""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}
        self.records: list[dict[str, Any]] = []
        self.is_valid: bool = False
        self.errors: list[str] = []

    def load_config(self, config_path: str) -> None:
        """Load privacy compliance settings from file.

        The configuration must contain ``allowed_regions`` (list of region
        codes) and ``data_retention_days`` (positive integer). ``ValueError``
        is raised if the configuration is missing or malformed.
        """

        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)

        allowed_regions = config.get("allowed_regions")
        retention = config.get("data_retention_days")
        if not isinstance(allowed_regions, list) or not allowed_regions:
            raise ValueError("allowed_regions missing or invalid")
        if not isinstance(retention, int) or retention <= 0:
            raise ValueError("data_retention_days missing or invalid")

        self.config = config

    def validate(self, records: Iterable[dict[str, Any]]) -> bool:
        """Validate data handling practices."""

        if not self.config:
            raise ValueError("Configuration not loaded")

        records_list = list(records)
        allowed_regions = {region for region in self.config["allowed_regions"]}
        retention = timedelta(days=int(self.config["data_retention_days"]))
        now = datetime.now(UTC)

        errors: list[str] = []
        for index, record in enumerate(records_list):
            if not record.get("consent"):
                errors.append(f"Record {index} missing consent")

            region = record.get("region")
            if region not in allowed_regions:
                errors.append(f"Record {index} has disallowed region: {region}")

            last_updated_str = record.get("last_updated")
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
            except (TypeError, ValueError) as exc:
                errors.append(
                    f"Record {index} has invalid last_updated timestamp: "
                    f"{last_updated_str!r} - {exc}"
                )
                continue
            except Exception:
                # Unexpected error - log and re-raise
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    "Unexpected error validating record %d",
                    index,
                    exc_info=True,
                    extra={"record": record},
                )
                raise

            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=UTC)
            else:
                last_updated = last_updated.astimezone(UTC)

            if now - last_updated > retention:
                errors.append(f"Record {index} exceeded retention period")

            record["last_updated"] = last_updated.isoformat()

        self.records = records_list
        self.errors = errors
        self.is_valid = not errors
        return self.is_valid

    def generate_report(self) -> str:
        """Create a compliance assessment report."""

        if not self.records and not self.errors:
            raise ValueError("No records validated")

        status = "passed" if self.is_valid else "failed"
        summary = f"Validation {status}. Records checked: {len(self.records)}."
        if self.errors:
            details = "\n".join(self.errors)
            return f"{summary}\nIssues:\n{details}"
        return summary
