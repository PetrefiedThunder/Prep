import json

import pytest

from auto_projection_bot.core import AutoProjectionBot


def write_config(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return path


def test_load_config(tmp_path):
    data = {"revenue": 1000, "expenses": 400, "growth_rate": 0.1}
    path = write_config(tmp_path, data)
    bot = AutoProjectionBot()
    bot.load_config(str(path))
    assert bot.config == data


def test_load_config_missing_file():
    bot = AutoProjectionBot()
    with pytest.raises(FileNotFoundError):
        bot.load_config("missing.json")


def test_validate_success(tmp_path):
    path = write_config(tmp_path, {"revenue": 1000, "expenses": 400})
    bot = AutoProjectionBot()
    bot.load_config(str(path))
    assert bot.validate() is True
    assert bot.validation_errors == []


def test_validate_missing_field(tmp_path):
    path = write_config(tmp_path, {"revenue": 1000})
    bot = AutoProjectionBot()
    bot.load_config(str(path))
    assert bot.validate() is False
    assert "Missing required field: expenses" in bot.generate_report()


def test_validate_type_error(tmp_path):
    path = write_config(tmp_path, {"revenue": "1000", "expenses": 400})
    bot = AutoProjectionBot()
    bot.load_config(str(path))
    assert bot.validate() is False
    report = bot.generate_report()
    assert "Field revenue must be numeric" in report


def test_generate_report(tmp_path):
    path = write_config(
        tmp_path,
        {"revenue": 1000, "expenses": 400, "growth_rate": 0.1},
    )
    bot = AutoProjectionBot()
    bot.load_config(str(path))
    report = bot.generate_report()
    assert "Revenue: 1000.0" in report
    assert "Expenses: 400.0" in report
    assert "Profit: 600.0" in report
    assert "Projected Revenue (next period): 1100.0" in report


def test_methods_run_end_to_end(tmp_path):
    path = write_config(
        tmp_path,
        {"revenue": 1000, "expenses": 400, "growth_rate": 0.1},
    )
    bot = AutoProjectionBot()
    assert bot.load_config(str(path)) is None
    assert bot.validate() is True
    report = bot.generate_report()
    assert "Projected Revenue (next period): 1100.0" in report
