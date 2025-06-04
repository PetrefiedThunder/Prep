"""Ergonomic Kitchen Matcher
===========================
Matches chefs to accessible kitchens based on mobility profile.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MobilityProfile:
    reach_angle: int
    max_transfer_height: int
    fine_motor_control: bool

@dataclass
class Kitchen:
    name: str
    accessible_height: int
    hallway_width: int

KITCHENS = [
    Kitchen(name="Station A", accessible_height=30, hallway_width=40),
    Kitchen(name="Station B", accessible_height=32, hallway_width=36),
]


def match_kitchen(profile: MobilityProfile) -> Optional[Kitchen]:
    for kitchen in KITCHENS:
        if kitchen.accessible_height <= profile.max_transfer_height and kitchen.hallway_width >= 36:
            return kitchen
    return None
