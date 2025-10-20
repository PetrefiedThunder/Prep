import json
import pytest

from lse_impact_simulator.core import LSEImpactSimulator


def _write_config(tmp_path, data=None):
    if data is None:
        data = {"market": "LSE", "volatility": 0.2, "duration": 5}
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    return config_path


def test_load_config(tmp_path):
    config_path = _write_config(tmp_path)
    simulator = LSEImpactSimulator()
    simulator.load_config(str(config_path))
    assert simulator.config["market"] == "LSE"


def test_load_config_missing_key(tmp_path):
    config_path = _write_config(tmp_path, {"market": "LSE", "volatility": 0.2})
    simulator = LSEImpactSimulator()
    with pytest.raises(ValueError):
        simulator.load_config(str(config_path))


def test_validate(tmp_path):
    simulator = LSEImpactSimulator()
    config_path = _write_config(tmp_path)
    simulator.load_config(str(config_path))
    assert simulator.validate() is True
    simulator.config["duration"] = 0
    assert simulator.validate() is False


def test_generate_report(tmp_path):
    simulator = LSEImpactSimulator()
    config_path = _write_config(tmp_path)
    simulator.load_config(str(config_path))
    report = simulator.generate_report()
    assert "Market: LSE" in report
    assert "Valid: True" in report


def test_generate_report_without_config():
    simulator = LSEImpactSimulator()
    with pytest.raises(ValueError):
        simulator.generate_report()

