import logging
import pytest
from phase12.mobility_ui_kit import TwoButtonNavigator


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
