"""Quiet Mode Core
=================
Global override system for sensory-sensitive users.
"""

import logging


logger = logging.getLogger(__name__)

class QuietMode:
    def __init__(self):
        self.enabled = False

    def toggle(self, state: bool):
        self.enabled = state
        if self.enabled:
            logger.info("Quiet mode activated. Disabling sounds and animations.")
        else:
            logger.info("Quiet mode deactivated.")
