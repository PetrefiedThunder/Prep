"""High level integrations that coordinate Prep modules."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

from modules.haptic_router.router import HapticRouter
from modules.prep_sync_agent.sensor_logger import PrepSyncAgent
from modules.voice_coach.coach import VoiceCoach

try:  # pragma: no cover - optional import for type checking
    from modules.kitchen_safety_daemon.daemon import SafetyDaemon
except Exception:  # pragma: no cover - fallback when optional deps missing
    SafetyDaemon = None  # type: ignore


class IntegrationCoordinator:
    """Coordinate cross-module integrations in a single place."""

    def __init__(
        self,
        sync_agent: PrepSyncAgent,
        voice_coach: VoiceCoach,
        haptic_router: HapticRouter,
    ) -> None:
        self.sync_agent = sync_agent
        self.voice_coach = voice_coach
        self.haptic_router = haptic_router

    def broadcast_alert(
        self,
        event: str,
        value: Any,
        *,
        voice_message: Optional[str] = None,
        haptic_mode: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log an event and trigger the connected feedback channels."""

        raw_payload = self.sync_agent.log_event(event, value, metadata=metadata)
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            payload = {"raw": raw_payload}

        voice_output = None
        if voice_message:
            voice_output = self.voice_coach.coach(voice_message)

        haptic_pattern = None
        if haptic_mode:
            haptic_pattern = self.haptic_router.route(haptic_mode)

        return {
            "event": payload,
            "voice": voice_output,
            "haptic": haptic_pattern,
        }

    def wire_safety_daemon(
        self,
        daemon: "SafetyDaemon",
        *,
        voice_template: str = "Safety notice: {message}",
        haptic_mode: str = "alert",
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Connect the safety daemon events into the coordinator pipeline."""

        if SafetyDaemon is None:  # pragma: no cover - safety check
            raise RuntimeError("Kitchen safety daemon module is not available")

        def _build_metadata() -> Dict[str, Any]:
            combined: Dict[str, Any] = {"source": "kitchen_safety_daemon"}
            if metadata:
                combined.update(metadata)
            return combined

        async def _handler(event: str, message: str) -> None:
            voice_message = voice_template.format(message=message)
            self.broadcast_alert(
                event,
                message,
                voice_message=voice_message,
                haptic_mode=haptic_mode,
                metadata=_build_metadata(),
            )

        daemon.set_event_handler(_handler)
