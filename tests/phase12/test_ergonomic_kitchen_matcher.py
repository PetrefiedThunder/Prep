import pytest

from phase12.ergonomic_kitchen_matcher import MobilityProfile, match_kitchen


pytestmark = pytest.mark.skip(
    reason="Legacy kitchen matcher components were removed with the orchestration cutover"
)


def test_kitchen_match(sample_profile):
    kitchen = match_kitchen(sample_profile)
    assert kitchen is not None
    assert kitchen.name == "Station A"


def test_kitchen_no_match():
    profile = MobilityProfile(reach_angle=45, max_transfer_height=20, fine_motor_control=True)
    assert match_kitchen(profile) is None
