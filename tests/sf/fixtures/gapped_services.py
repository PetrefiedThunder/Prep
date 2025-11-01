"""Fixture service module with intentional config mismatches."""


class DummyValidator:
    def __init__(self, config):
        self.business = config.get("business_registration", {})
        self.fire = config.get("fire", {})

    def evaluate(self):  # pragma: no cover - placeholder behaviour
        return bool(self.business) and bool(self.fire)
