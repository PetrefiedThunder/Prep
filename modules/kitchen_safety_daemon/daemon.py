import logging
import time
from typing import Callable, Optional


class SafetyDaemon:
    def __init__(self, check_interval: int = 60, logger: Optional[logging.Logger] = None):
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)

    def monitor(
        self,
        stop_flag: Optional[Callable[[], bool]] = None,
        iterations: Optional[int] = None,
    ) -> int:
        """Monitor safety conditions.

        Args:
            stop_flag: Callable returning True to stop the loop.
            iterations: Maximum number of iterations to run.

        Returns:
            The number of safety checks performed.
        """

        count = 0
        while True:
            if stop_flag and stop_flag():
                break
            if iterations is not None and count >= iterations:
                break
            # Placeholder for sensor checks
            self.logger.info("Performing safety check...")
            time.sleep(self.check_interval)
            count += 1
        return count
