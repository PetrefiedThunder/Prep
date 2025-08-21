import logging

from modules.haptic_router.router import HapticRouter


def test_route_logs_pattern(caplog):
    router = HapticRouter()
    with caplog.at_level(logging.INFO):
        pattern = router.route("start")
    assert pattern == [0.2]
    assert "Haptic pattern for start: [0.2]" in caplog.text
