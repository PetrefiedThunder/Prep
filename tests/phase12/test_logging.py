import logging

from phase12 import input_sense, mobility_ui_kit, quiet_mode_core


def test_configure_ui_logs(caplog):
    context = input_sense.SessionContext(["wheelchair"], "gesture-free")
    with caplog.at_level(logging.INFO):
        input_sense.configure_ui(context)
    assert "Configuring UI for ['wheelchair'] in gesture-free mode" in caplog.text


def test_two_button_navigator_logs_focus(caplog):
    navigator = mobility_ui_kit.TwoButtonNavigator(["a", "b"])
    with caplog.at_level(logging.INFO):
        navigator.move_down()
    assert "Focused on b" in caplog.text


def test_quiet_mode_toggle_logs(caplog):
    quiet = quiet_mode_core.QuietMode()
    with caplog.at_level(logging.INFO):
        quiet.toggle(True)
        quiet.toggle(False)
    assert "Quiet mode activated. Disabling sounds and animations." in caplog.text
    assert "Quiet mode deactivated." in caplog.text

