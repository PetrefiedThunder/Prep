"""Staffing integration clients."""

from .deputy import DeputyClient, DeputyError
from .seven_shifts import SevenShiftsClient, SevenShiftsError

__all__ = [
    "SevenShiftsClient",
    "SevenShiftsError",
    "DeputyClient",
    "DeputyError",
]
