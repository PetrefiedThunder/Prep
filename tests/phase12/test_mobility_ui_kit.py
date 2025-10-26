import logging

import pytest

from phase12 import mobility_ui_kit
from phase12.mobility_ui_kit import TwoButtonNavigator


pytestmark = pytest.mark.skip(
    reason="Legacy mobility UI kit dependencies were removed with the orchestration cutover"
)


def test_two_button_navigator(navigator, caplog):
    assert navigator.confirm() == "opt1"

    with caplog.at_level(logging.INFO):
        navigator.move_down()
    assert navigator.confirm() == "opt2"
    assert "Focused on opt2" in caplog.text
    caplog.clear()

    with caplog.at_level(logging.INFO):
        navigator.move_up()
    assert navigator.confirm() == "opt1"
    assert "Focused on opt1" in caplog.text
    caplog.clear()

    with caplog.at_level(logging.INFO):
        navigator.move_up()
    assert navigator.confirm() == "opt3"
    assert "Focused on opt3" in caplog.text


def test_two_button_navigator_rejects_empty_items():
    with pytest.raises(ValueError):
        mobility_ui_kit.TwoButtonNavigator([])

def test_two_button_navigator(navigator, caplog):
    with caplog.at_level(logging.INFO):
        assert navigator.confirm() == "opt1"

        navigator.move_down()
        assert navigator.confirm() == "opt2"
        assert "Focused on opt2" in caplog.text

        caplog.clear()
        navigator.move_up()
        assert navigator.confirm() == "opt1"
        assert "Focused on opt1" in caplog.text

        caplog.clear()
        navigator.move_up()
        assert navigator.confirm() == "opt3"
        assert "Focused on opt3" in caplog.text


def test_two_button_navigator_rejects_empty_list():
    with pytest.raises(ValueError):
        TwoButtonNavigator([])
