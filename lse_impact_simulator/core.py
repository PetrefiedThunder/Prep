import json
from pathlib import Path
from typing import Any, Dict

try:  # pragma: no cover - exercised via tests
    import yaml
except Exception:  # pragma: no cover - fallback if PyYAML missing
    yaml = None  # type: ignore[assignment]


class LSEImpactSimulator:
    """Simulates impacts for the London Stock Exchange environment."""

    EXPECTED_SCHEMA = {
        "market": str,
        "initial_price": (int, float),
        "volatility": (int, float),
    }

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}

    def load_config(self, config_path: str) -> None:
        """Load simulation configuration parameters from JSON or YAML."""
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as handle:
            if path.suffix.lower() in {".yaml", ".yml"}:
                if yaml is None:
                    raise ImportError("PyYAML is required for YAML configuration")
                self.config = yaml.safe_load(handle)
            else:
                self.config = json.load(handle)

    def validate(self) -> bool:
        """Validate scenario setup prior to simulation."""
        for key, types in self.EXPECTED_SCHEMA.items():
            value = self.config.get(key)
            if value is None or not isinstance(value, types):
                raise ValueError(f"Invalid or missing config field: {key}")
        return True

    def generate_report(self) -> str:
        """Report outcomes from the simulation run."""
        self.validate()

        market = self.config["market"]
        initial = float(self.config["initial_price"])
        volatility = float(self.config["volatility"])
        predicted_range = initial * volatility

        return (
            f"Market: {market}\n"
            f"Initial Price: {initial}\n"
            f"Volatility: {volatility}\n"
            f"Predicted Range: {predicted_range}"
        )
