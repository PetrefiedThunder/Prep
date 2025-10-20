import logging
from typing import List, Optional


class HapticRouter:
    """Map semantic modes to haptic feedback patterns."""

    PATTERNS = {
        "start": [0.2],
        "confirm": [0.1, 0.1],
        "alert": [0.5],
    }

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def route(self, mode: str) -> List[float]:
        pattern = list(self.PATTERNS.get(mode, []))
        if pattern:
            self.logger.info("Haptic pattern for %s: %s", mode, pattern)
        else:
            self.logger.warning("No haptic pattern configured for mode '%s'", mode)
        return pattern
