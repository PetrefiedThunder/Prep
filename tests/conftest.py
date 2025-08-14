import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from phase12.quiet_mode_core import QuietMode
from phase12.bci_signal_router import BCIRouter
from phase12.mobility_ui_kit import TwoButtonNavigator
from phase12.ergonomic_kitchen_matcher import MobilityProfile


@pytest.fixture
def quiet_mode():
    return QuietMode()


@pytest.fixture
def bci_router():
    return BCIRouter()


@pytest.fixture
def navigator():
    return TwoButtonNavigator(["opt1", "opt2", "opt3"])


@pytest.fixture
def sample_profile():
    return MobilityProfile(reach_angle=45, max_transfer_height=32, fine_motor_control=True)
