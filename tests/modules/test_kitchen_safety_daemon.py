import logging
import threading
import time

from modules.kitchen_safety_daemon.daemon import SafetyDaemon


def test_monitor_iterations(caplog):
    logger = logging.getLogger("test.daemon.iter")
    daemon = SafetyDaemon(check_interval=0, logger=logger)
    with caplog.at_level(logging.INFO, logger="test.daemon.iter"):
        daemon.monitor(iterations=2)
    assert caplog.text.count("Performing safety check...") == 2


def test_monitor_stop_flag(caplog):
    logger = logging.getLogger("test.daemon.stop")
    daemon = SafetyDaemon(check_interval=0.01, logger=logger)
    with caplog.at_level(logging.INFO, logger="test.daemon.stop"):
        thread = threading.Thread(target=daemon.monitor)
        thread.start()
        time.sleep(0.03)
        daemon.stop()
        thread.join(timeout=1)
    assert not thread.is_alive()
    assert "Performing safety check..." in caplog.text

