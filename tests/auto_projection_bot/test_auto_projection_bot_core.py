from auto_projection_bot.core import AutoProjectionBot


def test_methods_return_none():
    bot = AutoProjectionBot()
    assert bot.load_config('dummy_path') is None
    assert bot.validate() is None
    assert bot.generate_report() is None
