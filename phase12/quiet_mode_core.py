"""Quiet Mode Core
=================
Global override system for sensory-sensitive users.
"""

class QuietMode:
    def __init__(self):
        self.enabled = False

    def toggle(self, state: bool):
        self.enabled = state
        if self.enabled:
            print("Quiet mode activated. Disabling sounds and animations.")
        else:
            print("Quiet mode deactivated.")
