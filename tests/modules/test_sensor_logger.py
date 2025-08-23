import json
import logging
from datetime import datetime, timezone

from modules.prep_sync_agent.sensor_logger import PrepSyncAgent


def test_log_event_logs_json(caplog):
    logger = logging.getLogger("test.sensor_logger")
    agent = PrepSyncAgent("k1", logger=logger)
    with caplog.at_level(logging.INFO, logger="test.sensor_logger"):
        result = agent.log_event("temp", "100")
    data = json.loads(result)
    assert data["event"] == "temp"
    assert data["timestamp"].endswith("+00:00")
    assert datetime.fromisoformat(data["timestamp"]).tzinfo == timezone.utc
    assert result in caplog.text

