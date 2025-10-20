import json
from datetime import datetime, timezone
from datetime import datetime, timedelta, timezone

import pytest

from gdpr_ccpa_core.core import GDPRCCPACore


def make_config(tmp_path):
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({"allowed_regions": ["EU", "US"], "data_retention_days": 30}, handle)
    return config_path


def test_validate_success(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    records = [
        {
            "user_id": 1,
            "region": "EU",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "consent": True,
        }
    ]
    assert core.validate(records) is True
    report = core.generate_report()
    assert "Records checked: 1" in report


def test_validate_failure_consent(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    records = [
        {
            "user_id": 1,
            "region": "EU",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "consent": False,
        }
    ]
    assert core.validate(records) is False


def test_validate_generator_utc(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))

    record = {
        "user_id": 1,
        "region": "EU",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "consent": True,
    }

    def gen():
        yield record

    assert core.validate(gen()) is True
    assert core.records == [record]
    parsed = datetime.fromisoformat(core.records[0]["last_updated"])
    assert parsed.tzinfo == timezone.utc


def test_load_config_invalid(tmp_path):
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump({"data_retention_days": 30}, handle)
    core = GDPRCCPACore()
    with pytest.raises(ValueError):
        core.load_config(str(config_path))


def test_validate_generator_with_timezone(tmp_path):
    config_path = make_config(tmp_path)
    core = GDPRCCPACore()
    core.load_config(str(config_path))
    record = {
        "user_id": 1,
        "region": "EU",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "consent": True,
    }
    records = (r for r in [record])
    assert core.validate(records) is True
    assert core.records == [record]

