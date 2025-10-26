import logging

import pytest


pytestmark = pytest.mark.skip(
    reason="Legacy BCI router dependencies were removed with the orchestration cutover"
)


def test_bci_router_fallbacks(bci_router, caplog):
    with caplog.at_level(logging.INFO):
        bci_router.handle_signal(None)
        assert bci_router.active_mode == "eye_tracking"
        assert "BCI failed" in caplog.text
        caplog.clear()

        bci_router.handle_signal(None)
        assert bci_router.active_mode == "voice"
        assert "Eye-tracking failed" in caplog.text
        caplog.clear()

        bci_router.handle_signal("ping")
        assert "Received signal in voice mode" in caplog.text
