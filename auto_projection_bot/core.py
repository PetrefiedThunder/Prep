from __future__ import annotations

from typing import Any

from prep.utility.config_schema import BaseConfigSchema


class AutoProjectionBot(BaseConfigSchema):
    """Generates automated financial projections."""

    def __init__(self, *, logger=None) -> None:
        super().__init__(logger=logger)

    def load_config(self, config_path: str) -> None:  # type: ignore[override]
        super().load_config(config_path)

    def _run_validation(self) -> list[str]:  # type: ignore[override]
        errors: list[str] = []
        config: dict[str, Any] = self.config

        for field in ("revenue", "expenses"):
            if field not in config:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(config[field], (int, float)):
                errors.append(f"Field {field} must be numeric")

        growth = config.get("growth_rate", 0)
        if growth is not None and not isinstance(growth, (int, float)):
            errors.append("growth_rate must be numeric")

        return errors

    def validate(self) -> bool:  # type: ignore[override]
        return super().validate()

    def generate_report(self) -> str:  # type: ignore[override]
        self.ensure_config_loaded()
        if not self._validated:
            self.validate()

        if self.validation_errors:
            return super().generate_report()

        revenue = float(self.config["revenue"])
        expenses = float(self.config["expenses"])
        growth_rate = float(self.config.get("growth_rate", 0))

        profit = revenue - expenses
        projected_revenue = revenue * (1 + growth_rate)

        return (
            f"Revenue: {revenue}\n"
            f"Expenses: {expenses}\n"
            f"Profit: {profit}\n"
            f"Projected Revenue (next period): {projected_revenue}"
        )
