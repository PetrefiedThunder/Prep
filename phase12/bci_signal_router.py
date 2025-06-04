"""BCI Signal Router
===================
Future-ready Brain-Computer Interface hooks with fallback.
"""

class BCIRouter:
    def __init__(self):
        self.active_mode = "bci"

    def handle_signal(self, signal):
        if self.active_mode == "bci" and signal is None:
            print("BCI failed, falling back to eye-tracking")
            self.active_mode = "eye_tracking"
        elif self.active_mode == "eye_tracking" and signal is None:
            print("Eye-tracking failed, using voice control")
            self.active_mode = "voice"
        else:
            print(f"Received signal in {self.active_mode} mode")
