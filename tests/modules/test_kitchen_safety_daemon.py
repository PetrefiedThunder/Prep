import logging

from modules.kitchen_safety_daemon.daemon import SafetyDaemon


def test_monitor_iterations(caplog):
    daemon = SafetyDaemon(check_interval=0)
    with caplog.at_level(logging.INFO):
        count = daemon.monitor(iterations=2)
    assert count == 2
    assert caplog.text.count("Performing safety check...") == 2


def test_monitor_stop_flag(caplog):
    daemon = SafetyDaemon(check_interval=0)
    stop_iter = iter([False, True])

    def stop_flag():
        return next(stop_iter)

    with caplog.at_level(logging.INFO):
        count = daemon.monitor(stop_flag=stop_flag)
    assert count == 1
    assert caplog.text.count("Performing safety check...") == 1
