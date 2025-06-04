"""Mobility-First UI Kit
=======================
Provides 2-button, eye-tracking, and joystick-optimized UI helpers.
"""

class TwoButtonNavigator:
    """Simple navigation model using up/confirm interactions."""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def move_up(self):
        self.index = (self.index - 1) % len(self.items)
        self.announce()

    def move_down(self):
        self.index = (self.index + 1) % len(self.items)
        self.announce()

    def confirm(self):
        return self.items[self.index]

    def announce(self):
        print(f"Focused on {self.items[self.index]}")
