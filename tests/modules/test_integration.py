import asyncio
import logging
from unittest.mock import MagicMock

from modules.integration import IntegrationCoordinator
from modules.kitchen_safety_daemon.daemon import SafetyDaemon
from modules.prep_sync_agent.sensor_logger import PrepSyncAgent
from modules.voice_coach.coach import VoiceCoach
from modules.haptic_router.router import HapticRouter


def _fast_sleep(_: float) -> None:
    return None


def test_broadcast_alert_coordinated(caplog):
    logger = logging.getLogger("test.integration.broadcast")
    agent = PrepSyncAgent("k1", logger=logger)
    voice = VoiceCoach(tone="direct", logger=logger)
    haptics = HapticRouter(logger=logger)
    coordinator = IntegrationCoordinator(agent, voice, haptics)

    with caplog.at_level(logging.INFO, logger="test.integration.broadcast"):
        result = coordinator.broadcast_alert(
            "temp_high",
            205,
            voice_message="Temperature is elevated",
            haptic_mode="alert",
            metadata={"severity": "high"},
        )

    assert result["event"]["event"] == "temp_high"
    assert result["event"]["value"] == 205
    assert result["event"]["metadata"] == {"severity": "high"}
    assert result["voice"] == "Heads up: Temperature is elevated"
    assert result["haptic"] == [0.5]
    assert "Heads up: Temperature is elevated" in caplog.text


def test_wire_safety_daemon_invokes_broadcast():
    logger = logging.getLogger("test.integration.daemon")
    agent = PrepSyncAgent("k2", logger=logger)
    voice = VoiceCoach(tone="gentle", logger=logger)
    haptics = HapticRouter(logger=logger)
    coordinator = IntegrationCoordinator(agent, voice, haptics)

    daemon = SafetyDaemon(check_interval=0, logger=logger, sleep_fn=_fast_sleep)

    coordinator.broadcast_alert = MagicMock(  # type: ignore[assignment]
        wraps=coordinator.broadcast_alert
    )

    coordinator.wire_safety_daemon(
        daemon,
        voice_template="Alert: {message}",
        haptic_mode="confirm",
        metadata={"severity": "low"},
    )

    async def run() -> None:
        await daemon.monitor(iterations=1)

    asyncio.run(run())

    coordinator.broadcast_alert.assert_called_once()
    args, kwargs = coordinator.broadcast_alert.call_args
    assert args[0] == "safety_check"
    assert args[1] == "Performing safety check..."
    assert kwargs["voice_message"] == "Alert: Performing safety check..."
    assert kwargs["haptic_mode"] == "confirm"
    assert kwargs["metadata"]["severity"] == "low"
    assert kwargs["metadata"]["source"] == "kitchen_safety_daemon"
