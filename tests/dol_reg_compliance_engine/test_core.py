import json

import pytest

from dol_reg_compliance_engine.core import DOLRegComplianceEngine


def make_config(tmp_path, data=None):
    config_path = tmp_path / "config.json"
    payload = data or {"minimum_wage": 15.0, "max_hours_per_week": 40}
    config_path.write_text(json.dumps(payload))
    return config_path


def test_validate_success(tmp_path):
    config_path = make_config(tmp_path)
    engine = DOLRegComplianceEngine()
    engine.load_config(str(config_path))
    data = [{"wage": 16.0, "hours_worked": 35}]
    assert engine.validate(data) is True
    report = engine.generate_report()
    assert "Records checked: 1" in report
    assert "Compliant: True" in report


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
    report = engine.generate_report()
    assert "Errors" in report


def test_validate_missing_fields(tmp_path):
    config_path = make_config(tmp_path)
    engine = DOLRegComplianceEngine()
    engine.load_config(str(config_path))
    data = [{}]
    assert engine.validate(data) is False
    report = engine.generate_report()
    assert "missing wage" in report
    assert "missing hours_worked" in report


def test_load_config_invalid(tmp_path):
    config_path = make_config(tmp_path, {"minimum_wage": -1})
    engine = DOLRegComplianceEngine()
    with pytest.raises(ValueError):
        engine.load_config(str(config_path))
