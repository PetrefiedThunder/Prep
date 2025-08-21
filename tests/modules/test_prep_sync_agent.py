import json
import logging

from modules.prep_sync_agent.sensor_logger import PrepSyncAgent


def test_log_event_logs_json(caplog):
    agent = PrepSyncAgent("k1")
    with caplog.at_level(logging.INFO):
        json_data = agent.log_event("temp", "high")
    data = json.loads(json_data)
    assert data["event"] == "temp"
    assert json_data in caplog.text
