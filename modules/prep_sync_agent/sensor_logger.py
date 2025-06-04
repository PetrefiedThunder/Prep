import json
from datetime import datetime

class PrepSyncAgent:
    def __init__(self, kitchen_id: str):
        self.kitchen_id = kitchen_id

    def log_event(self, event: str, value: str) -> str:
        data = {
            "kitchen_id": self.kitchen_id,
            "event": event,
            "value": value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        json_data = json.dumps(data)
        print(json_data)
        return json_data
