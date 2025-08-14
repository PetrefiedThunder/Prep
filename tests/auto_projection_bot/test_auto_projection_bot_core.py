import json

from auto_projection_bot.core import AutoProjectionBot


def test_methods_run_end_to_end(tmp_path):
    data = {"revenue": 1000, "expenses": 400, "growth_rate": 0.1}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))

    bot = AutoProjectionBot()

    assert bot.load_config(str(config_file)) is None
    assert bot.validate() is True

    report = bot.generate_report()
    assert "Revenue: 1000.0" in report
    assert "Expenses: 400.0" in report
