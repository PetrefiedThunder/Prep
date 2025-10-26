import pytest


pytestmark = pytest.mark.skip(
    reason="Legacy quiet mode helpers were removed with the orchestration cutover"
)


def test_quiet_mode_toggle(quiet_mode, capsys):
    quiet_mode.toggle(True)
    captured = capsys.readouterr()
    assert quiet_mode.enabled is True
    assert "Quiet mode activated" in captured.out

    quiet_mode.toggle(False)
    captured = capsys.readouterr()
    assert quiet_mode.enabled is False
    assert "Quiet mode deactivated" in captured.out
