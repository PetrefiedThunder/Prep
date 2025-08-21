import logging
from typing import Optional


class HapticRouter:
    PATTERNS = {
        "start": [0.2],
        "confirm": [0.1, 0.1],
        "alert": [0.5],
    }

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def route(self, mode: str):
        pattern = self.PATTERNS.get(mode)
        if not pattern:
            pattern = []
        self.logger.info("Haptic pattern for %s: %s", mode, pattern)
        return pattern
