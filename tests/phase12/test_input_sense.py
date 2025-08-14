from phase12.input_sense import SessionContext, detect_input_devices, configure_ui


def test_detect_input_devices():
    ctx = detect_input_devices()
    assert "wheelchair" in ctx.input_mode
    assert ctx.ui_mode == "gesture-free"


def test_configure_ui(capsys):
    ctx = SessionContext(input_mode=["voice"], ui_mode="default")
    configure_ui(ctx)
    captured = capsys.readouterr()
    assert "Configuring UI for ['voice'] in default mode" in captured.out
