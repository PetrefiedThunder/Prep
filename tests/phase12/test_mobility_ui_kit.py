
def test_two_button_navigator(navigator, capsys):
    assert navigator.confirm() == "opt1"

    navigator.move_down()
    captured = capsys.readouterr()
    assert navigator.confirm() == "opt2"
    assert "Focused on opt2" in captured.out

    navigator.move_up()
    captured = capsys.readouterr()
    assert navigator.confirm() == "opt1"
    assert "Focused on opt1" in captured.out

    navigator.move_up()
    captured = capsys.readouterr()
    assert navigator.confirm() == "opt3"
    assert "Focused on opt3" in captured.out
