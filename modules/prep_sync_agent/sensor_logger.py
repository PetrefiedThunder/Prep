import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

class PrepSyncAgent:
    def __init__(self, kitchen_id: str, logger: Optional[logging.Logger] = None):
        self.kitchen_id = kitchen_id
        self.logger = logger or logging.getLogger(__name__)

    def log_event(
        self,
        event: str,
        value: Any,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Record a kitchen sensor event as JSON.

        Parameters
        ----------
        event:
            The event name that should be recorded.
        value:
            Any value associated with the event. Values that are not
            JSON-serialisable are automatically converted to strings.
        metadata:
            Optional structured details to embed alongside the event.
        """

        data = {
            "kitchen_id": self.kitchen_id,
            "event": event,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            data["metadata"] = dict(metadata)
        json_data = json.dumps(data, default=str)
        self.logger.info(json_data)
        return json_data
