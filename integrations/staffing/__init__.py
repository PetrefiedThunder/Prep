"""Staffing integration clients."""

from .seven_shifts import SevenShiftsClient, SevenShiftsError
from .deputy import DeputyClient, DeputyError

__all__ = [
    "SevenShiftsClient",
    "SevenShiftsError",
    "DeputyClient",
    "DeputyError",
]
