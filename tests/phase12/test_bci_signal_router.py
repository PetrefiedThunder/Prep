
def test_bci_router_fallbacks(bci_router, capsys):
    bci_router.handle_signal(None)
    captured = capsys.readouterr()
    assert bci_router.active_mode == "eye_tracking"
    assert "BCI failed" in captured.out

    bci_router.handle_signal(None)
    captured = capsys.readouterr()
    assert bci_router.active_mode == "voice"
    assert "Eye-tracking failed" in captured.out

    bci_router.handle_signal("ping")
    captured = capsys.readouterr()
    assert "Received signal in voice mode" in captured.out
