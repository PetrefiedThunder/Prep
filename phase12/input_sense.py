"""Input Sense Module
=====================
Detects assistive devices and configures UI automatically.
"""

from dataclasses import dataclass
from typing import List
import logging


logger = logging.getLogger(__name__)

@dataclass
class SessionContext:
    input_mode: List[str]
    ui_mode: str
    assistive_routing: bool = True


def detect_input_devices() -> SessionContext:
    """Mock detection logic for assistive devices."""
    # Placeholder: integrate with actual hardware APIs
    devices = ["wheelchair", "eye_tracking"]
    return SessionContext(input_mode=devices, ui_mode="gesture-free")


def configure_ui(context: SessionContext) -> None:
    """Apply UI configuration based on detected devices."""
    logger.info("Configuring UI for %s in %s mode", context.input_mode, context.ui_mode)
