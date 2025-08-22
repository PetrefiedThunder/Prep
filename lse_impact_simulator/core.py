import json
from typing import Any, Dict


class LSEImpactSimulator:
    """Simulates impacts for the London Stock Exchange environment."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.is_valid: bool = False

    def load_config(self, config_path: str) -> None:
        """Load simulation configuration parameters.

        Expected schema::

            {
                "market": str,
                "volatility": float,
                "duration": int,
            }

        ``volatility`` must be a non-negative value representing the expected
        daily volatility percentage and ``duration`` must be a positive number
        of trading days.
        """

        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        schema = {
            "market": str,
            "volatility": (int, float),
            "duration": int,
        }

        for key, expected_type in schema.items():
            if key not in data:
                raise ValueError(f"Missing required config key: {key}")
            if not isinstance(data[key], expected_type):
                raise TypeError(f"Invalid type for {key}: expected {expected_type}")

        self.config = data

    def validate(self) -> bool:
        """Validate scenario setup prior to simulation."""

        if not self.config:
            self.is_valid = False
            return False

        market = self.config.get("market")
        volatility = self.config.get("volatility")
        duration = self.config.get("duration")

        if not isinstance(market, str) or not market.strip():
            self.is_valid = False
            return False

        if not isinstance(volatility, (int, float)) or volatility < 0:
            self.is_valid = False
            return False

        if not isinstance(duration, int) or duration <= 0:
            self.is_valid = False
            return False

        self.is_valid = True
        return True

    def generate_report(self) -> str:
        """Report outcomes from the simulation run."""

        if not self.config:
            raise ValueError("Configuration not loaded")

        valid = self.validate()

        return (
            f"Market: {self.config['market']}, "
            f"Volatility: {self.config['volatility']}, "
            f"Duration: {self.config['duration']}, "
            f"Valid: {valid}"
        )
