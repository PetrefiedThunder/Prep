import json
import pytest
from prep import initialize, utility


def create_config(tmp_path, data):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))
    return initialize(str(config_file))


def test_util_func_returns_value(tmp_path):
    config = create_config(tmp_path, {"answer": 42})
    assert utility.util_func(config, "answer") == 42


def test_util_func_uses_default(tmp_path):
    config = create_config(tmp_path, {})
    assert utility.util_func(config, "missing", default="fallback") == "fallback"


def test_util_func_missing_key(tmp_path):
    config = create_config(tmp_path, {})
    with pytest.raises(KeyError):
        utility.util_func(config, "missing")
