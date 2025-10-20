import json
from datetime import datetime

import pytest

from dol_reg_compliance_engine.core import DOLRegComplianceEngine


def make_config(tmp_path):
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({"minimum_wage": 15.0, "max_hours_per_week": 40}, handle)
    return config_path


def test_validate_success(tmp_path):
    config_path = make_config(tmp_path)
    engine = DOLRegComplianceEngine()
    engine.load_config(str(config_path))
    data = [{"wage": 16.0, "hours_worked": 35}]
    assert engine.validate(data) is True
    report = engine.generate_report()
    assert "Records checked: 1" in report


def test_validate_generator_records_persist(tmp_path):
    config_path = make_config(tmp_path)
    engine = DOLRegComplianceEngine()
    engine.load_config(str(config_path))

    def record_gen():
        yield {"wage": 16.0, "hours_worked": 35}
        yield {"wage": 17.0, "hours_worked": 30}

    assert engine.validate(record_gen()) is True
    report = engine.generate_report()
    assert "Records checked: 2" in report
    assert len(engine.records) == 2


def test_validate_failure_low_wage(tmp_path):
    config_path = make_config(tmp_path)
    engine = DOLRegComplianceEngine()
    engine.load_config(str(config_path))
    data = [{"wage": 10.0, "hours_worked": 35}]
    assert engine.validate(data) is False


def test_load_config_invalid(tmp_path):
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({"minimum_wage": -1}, handle)
    engine = DOLRegComplianceEngine()
    with pytest.raises(ValueError):
        engine.load_config(str(config_path))

