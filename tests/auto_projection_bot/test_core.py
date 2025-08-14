import json
import pytest
from auto_projection_bot.core import AutoProjectionBot


def test_load_config(tmp_path):
    data = {"revenue": 1000, "expenses": 400, "growth_rate": 0.1}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    bot = AutoProjectionBot()
    bot.load_config(str(config_file))
    assert bot.config == data


def test_load_config_missing_file():
    bot = AutoProjectionBot()
    with pytest.raises(FileNotFoundError):
        bot.load_config("missing.json")


def test_validate_success(tmp_path):
    data = {"revenue": 1000, "expenses": 400}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    bot = AutoProjectionBot()
    bot.load_config(str(config_file))
    assert bot.validate() is True


def test_validate_missing_field(tmp_path):
    data = {"revenue": 1000}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    bot = AutoProjectionBot()
    bot.load_config(str(config_file))
    with pytest.raises(ValueError):
        bot.validate()


def test_validate_type_error(tmp_path):
    data = {"revenue": "1000", "expenses": 400}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    bot = AutoProjectionBot()
    bot.load_config(str(config_file))
    with pytest.raises(ValueError):
        bot.validate()


def test_generate_report(tmp_path):
    data = {"revenue": 1000, "expenses": 400, "growth_rate": 0.1}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    bot = AutoProjectionBot()
    bot.load_config(str(config_file))
    report = bot.generate_report()
    assert "Revenue: 1000.0" in report
    assert "Expenses: 400.0" in report
    assert "Profit: 600.0" in report
    assert "Projected Revenue (next period): 1100.0" in report
