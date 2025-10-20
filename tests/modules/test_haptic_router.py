import logging

from modules.haptic_router.router import HapticRouter


def test_route_logs_pattern(caplog):
    logger = logging.getLogger("test.haptic_router")
    router = HapticRouter(logger=logger)
    with caplog.at_level(logging.INFO, logger="test.haptic_router"):
        pattern = router.route("confirm")
    assert pattern == [0.1, 0.1]
    assert "Haptic pattern for confirm: [0.1, 0.1]" in caplog.text

