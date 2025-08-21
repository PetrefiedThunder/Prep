import logging
import time
from typing import Optional


class SafetyDaemon:
    def __init__(self, check_interval: int = 60, logger: Optional[logging.Logger] = None):
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def monitor(self, iterations: Optional[int] = None) -> None:
        count = 0
        while not self._stop:
            # Placeholder for sensor checks
            self.logger.info("Performing safety check...")
            time.sleep(self.check_interval)
            count += 1
            if iterations is not None and count >= iterations:
                break
