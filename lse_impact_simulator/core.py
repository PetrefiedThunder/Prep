from __future__ import annotations

from typing import Any, Dict, List

from prep.utility.config_schema import BaseConfigSchema


class LSEImpactSimulator(BaseConfigSchema):
    """Simulates impacts for the London Stock Exchange environment."""

    EXPECTED_SCHEMA = {
        "market": str,
        "initial_price": (int, float),
        "volatility": (int, float),
        "duration": int,
    }

    def __init__(self, *, logger=None) -> None:
        super().__init__(logger=logger)
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:  # type: ignore[override]
        super().load_config(config_path)

    def validate(self) -> bool:  # type: ignore[override]
        return super().validate()

    def _run_validation(self) -> List[str]:  # type: ignore[override]
        config = self.config
        errors: List[str] = []

        for field, expected in self.EXPECTED_SCHEMA.items():
            value = config.get(field)
            if value is None or not isinstance(value, expected):
                errors.append(f"Invalid or missing config field: {field}")

        volatility = config.get("volatility")
        if isinstance(volatility, (int, float)) and float(volatility) < 0:
            errors.append("volatility must be non-negative")

        duration = config.get("duration")
        if isinstance(duration, int) and duration <= 0:
            errors.append("duration must be positive")

        self.is_valid = not errors
        return errors

    def generate_report(self) -> str:  # type: ignore[override]
        self.ensure_config_loaded()
        if not self._validated:
            self.validate()

        if self.validation_errors:
            return super().generate_report()

        market = self.config["market"]
        initial = float(self.config["initial_price"])
        volatility = float(self.config["volatility"])
        duration = int(self.config["duration"])
        predicted_range = initial * volatility
        projected_close = initial + predicted_range

        return (
            f"Market: {market}\n"
            f"Initial Price: {initial}\n"
            f"Volatility: {volatility}\n"
            f"Duration: {duration}\n"
            f"Predicted Range: ±{predicted_range}\n"
            f"Projected Close: {projected_close}"
        )
