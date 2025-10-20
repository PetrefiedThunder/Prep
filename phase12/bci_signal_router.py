"""BCI Signal Router
===================
Future-ready Brain-Computer Interface hooks with fallback.
"""

import logging


logger = logging.getLogger(__name__)

class BCIRouter:
    def __init__(self):
        self.active_mode = "bci"

    def handle_signal(self, signal):
        if self.active_mode == "bci" and signal is None:
            logger.info("BCI failed, falling back to eye-tracking")
            self.active_mode = "eye_tracking"
        elif self.active_mode == "eye_tracking" and signal is None:
            logger.info("Eye-tracking failed, using voice control")
            self.active_mode = "voice"
        else:
            logger.info("Received signal in %s mode", self.active_mode)
