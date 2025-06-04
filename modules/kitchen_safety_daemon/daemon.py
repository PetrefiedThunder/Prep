import time

class SafetyDaemon:
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval

    def monitor(self):
        while True:
            # Placeholder for sensor checks
            print("Performing safety check...")
            time.sleep(self.check_interval)
