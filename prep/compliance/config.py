from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class ComplianceConfig:
    """Configuration for compliance engines."""

    enabled_engines: list[str]
    audit_frequency: str
    notification_threshold: float
    report_format: str
    storage_path: str
    retention_days: int
    enable_simulations: bool
    custom_rules_path: str | None = None


class ComplianceConfigManager:
    """Manages compliance configuration."""

    def __init__(self, config_path: str = "config/compliance.yaml") -> None:
        self.config_path = config_path
        self.config: ComplianceConfig | None = None
        self.load_config()

    def load_config(self) -> None:
        if os.path.exists(self.config_path):
            with open(self.config_path, encoding="utf-8") as handle:
                config_data = yaml.safe_load(handle) or {}
            self.config = ComplianceConfig(**config_data)
        else:
            self.config = ComplianceConfig(
                enabled_engines=["dol", "privacy", "hbs", "lse", "ui"],
                audit_frequency="weekly",
                notification_threshold=0.8,
                report_format="json",
                storage_path="./compliance_reports",
                retention_days=90,
                enable_simulations=True,
            )

    def save_config(self) -> None:
        if not self.config:
            raise ValueError("No configuration loaded")

        directory = os.path.dirname(self.config_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        config_dict = {
            "enabled_engines": self.config.enabled_engines,
            "audit_frequency": self.config.audit_frequency,
            "notification_threshold": self.config.notification_threshold,
            "report_format": self.config.report_format,
            "storage_path": self.config.storage_path,
            "retention_days": self.config.retention_days,
            "enable_simulations": self.config.enable_simulations,
            "custom_rules_path": self.config.custom_rules_path,
        }

        with open(self.config_path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(config_dict, handle)

    def get_engine_config(self, engine_name: str) -> dict[str, Any]:
        if not self.config:
            raise ValueError("Configuration not loaded")
        return {
            "enabled": engine_name in self.config.enabled_engines,
            "notification_threshold": self.config.notification_threshold,
        }
