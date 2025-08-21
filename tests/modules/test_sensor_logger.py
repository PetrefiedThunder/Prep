import json
import logging

from modules.prep_sync_agent.sensor_logger import PrepSyncAgent


def test_log_event_logs_json(caplog):
    logger = logging.getLogger("test.sensor_logger")
    agent = PrepSyncAgent("k1", logger=logger)
    with caplog.at_level(logging.INFO, logger="test.sensor_logger"):
        result = agent.log_event("temp", "100")
    assert json.loads(result)["event"] == "temp"
    assert result in caplog.text

