"""Shared configuration schema helpers for Prep modules."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import IO, Any

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback when PyYAML unavailable
    yaml = None  # type: ignore[assignment]


class BaseConfigSchema(ABC):
    """Base helper implementing common config and reporting behaviour."""

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        config_required: bool = True,
    ) -> None:
        self.logger = logger or logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self.config: dict[str, Any] = {}
        self._validation_errors: list[str] = []
        self._validated: bool = False
        self._config_required = config_required

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def load_config(self, config_path: str) -> dict[str, Any]:
        """Load configuration data from ``config_path``.

        JSON files are supported out of the box. YAML files can also be used
        when :mod:`PyYAML` is installed. Sub-classes may override
        :meth:`_normalise_config` for additional processing.
        """

        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            raw_config = self._read_config(handle, path)

        if not isinstance(raw_config, Mapping):
            raise TypeError("Configuration must contain a mapping")

        self.config = self._normalise_config(dict(raw_config))
        self._validation_errors.clear()
        self._validated = False
        self.logger.debug("Loaded configuration from %s", path)
        return self.config

    def _read_config(self, handle: IO[str], path: Path) -> Mapping[str, Any]:
        if path.suffix.lower() in {".yaml", ".yml"}:
            if yaml is None:  # pragma: no cover - defensive
                raise ImportError("PyYAML is required to load YAML configurations")
            data = yaml.safe_load(handle)
        else:
            data = json.load(handle)
        return data  # type: ignore[return-value]

    def _normalise_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return config

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate(self, *args: Any, **kwargs: Any) -> bool:
        self.ensure_config_loaded()
        self._validation_errors = self._run_validation(*args, **kwargs)
        self._validated = not self._validation_errors
        if self._validation_errors:
            for error in self._validation_errors:
                self.logger.warning(error)
        else:
            self.logger.info("Validation passed")
        return self._validated

    @abstractmethod
    def _run_validation(self, *args: Any, **kwargs: Any) -> list[str]:
        """Return a list of validation error messages."""

    def ensure_config_loaded(self) -> dict[str, Any]:
        if self._config_required and not self.config:
            raise ValueError("Configuration not loaded")
        return self.config

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def generate_report(self) -> str:
        """Return a standardised validation report."""

        if not self._validated and not self._validation_errors:
            raise ValueError("Validation has not been run")

        status = "passed" if not self._validation_errors else "failed"
        lines = [f"Validation {status}."]
        if self._validation_errors:
            lines.append("Errors:")
            lines.extend(f"- {message}" for message in self._validation_errors)
        report = "\n".join(lines)
        self.logger.debug("Generated report: %s", report)
        return report

    @property
    def validation_errors(self) -> list[str]:
        return list(self._validation_errors)


class IterableValidationMixin:
    """Mixin providing helper to coerce iterables to a list."""

    def _ensure_list(self, items: Iterable[Any]) -> list[Any]:
        if isinstance(items, list):
            return items
        return list(items)
