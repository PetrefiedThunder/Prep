import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


class PrepSyncAgent:
    """Serialize and log kitchen sensor events."""

    def __init__(self, kitchen_id: str, logger: Optional[logging.Logger] = None) -> None:
        self.kitchen_id = kitchen_id
        self.logger = logger or logging.getLogger(__name__)

    def log_event(
        self,
        event: str,
        value: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> str:
        data = {
            "kitchen_id": self.kitchen_id,
            "event": event,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            data["metadata"] = dict(metadata)

        payload = json.dumps(data, default=str)
        self.logger.info(payload)
        return payload
