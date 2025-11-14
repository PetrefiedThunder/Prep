import json
from datetime import UTC, datetime, timedelta

import pytest

from gdpr_ccpa_core.core import GDPRCCPACore


def make_config(tmp_path, data=None):
    payload = data or {"allowed_regions": ["EU", "US"], "data_retention_days": 30}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload))
    return config_path


def fresh_record(**overrides):
    base = {
        "user_id": 1,
        "region": "EU",
        "last_updated": datetime.now(UTC).isoformat(),
        "consent": True,
    }
    base.update(overrides)
    return base


def test_validate_success(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    records = [fresh_record()]
    assert core.validate(records) is True
    report = core.generate_report()
    assert "Validation passed" in report
    assert "Records checked: 1" in report


def test_validate_failure_consent(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    records = [fresh_record(consent=False)]
    assert core.validate(records) is False
    report = core.generate_report()
    assert "missing consent" in report


def test_validate_generator_utc(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    record = fresh_record()

    def gen():
        yield record

    assert core.validate(gen()) is True
    assert core.records == [record]
    parsed = datetime.fromisoformat(core.records[0]["last_updated"])
    assert parsed.tzinfo == UTC


def test_retention_enforced(tmp_path):
    config_path = make_config(tmp_path, {"allowed_regions": ["EU"], "data_retention_days": 1})
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    stale = fresh_record(last_updated=(datetime.now(UTC) - timedelta(days=5)).isoformat())
    assert core.validate([stale]) is False
    assert "exceeded retention" in core.generate_report()


def test_load_config_invalid(tmp_path):
    config_path = make_config(tmp_path, {"data_retention_days": 30})
    core = GDPRCCPACore()
    with pytest.raises(ValueError):
        core.load_config(str(config_path))
