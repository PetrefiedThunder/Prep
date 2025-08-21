import json
import logging
from datetime import datetime
from typing import Optional


class PrepSyncAgent:
    def __init__(self, kitchen_id: str, logger: Optional[logging.Logger] = None):
        self.kitchen_id = kitchen_id
        self.logger = logger or logging.getLogger(__name__)

    def log_event(self, event: str, value: str) -> str:
        data = {
            "kitchen_id": self.kitchen_id,
            "event": event,
            "value": value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        json_data = json.dumps(data)
        self.logger.info(json_data)
        return json_data
