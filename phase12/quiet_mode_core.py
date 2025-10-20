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
            message = "Quiet mode activated. Disabling sounds and animations."
        else:
            message = "Quiet mode deactivated."
        logger.info(message)
        print(message)
