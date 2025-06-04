class HapticRouter:
    PATTERNS = {
        "start": [0.2],
        "confirm": [0.1, 0.1],
        "alert": [0.5],
    }

    def route(self, mode: str):
        pattern = self.PATTERNS.get(mode)
        if not pattern:
            pattern = []
        print(f"Haptic pattern for {mode}: {pattern}")
        return pattern
