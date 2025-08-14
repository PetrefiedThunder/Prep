import json
from pathlib import Path


class AutoProjectionBot:
    """Generates automated financial projections."""

    def __init__(self) -> None:
        self.config: dict | None = None

    def load_config(self, config_path: str) -> None:
        """Load projection parameters from configuration."""
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as f:
            self.config = json.load(f)

    def validate(self) -> bool:
        """Validate projection assumptions and inputs."""
        if self.config is None:
            raise ValueError("Configuration not loaded")

        required = ["revenue", "expenses"]
        for key in required:
            if key not in self.config:
                raise ValueError(f"Missing required field: {key}")
            if not isinstance(self.config[key], (int, float)):
                raise ValueError(f"Field {key} must be numeric")

        growth = self.config.get("growth_rate", 0)
        if growth is not None and not isinstance(growth, (int, float)):
            raise ValueError("growth_rate must be numeric")

        return True

    def generate_report(self) -> str:
        """Compile a projection summary for review."""
        self.validate()

        revenue = float(self.config["revenue"])  # type: ignore[index]
        expenses = float(self.config["expenses"])  # type: ignore[index]
        growth_rate = float(self.config.get("growth_rate", 0))  # type: ignore[arg-type]

        profit = revenue - expenses
        projected_revenue = revenue * (1 + growth_rate)

        return (
            f"Revenue: {revenue}\n"
            f"Expenses: {expenses}\n"
            f"Profit: {profit}\n"
            f"Projected Revenue (next period): {projected_revenue}"
        )
