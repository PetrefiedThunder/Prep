import importlib
import json

import pytest

import prep


@pytest.fixture
def fresh_prep():
    """Reload the :mod:`prep` module to reset cached configuration."""
    importlib.reload(prep)
    return prep


def test_initialize(tmp_path, fresh_prep):
    config_data = {"option": "value"}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    result = fresh_prep.initialize(str(config_file))
    assert result == config_data


def test_initialize_uses_env_var(tmp_path, monkeypatch, fresh_prep):
    config_data = {"foo": "bar"}
    config_file = tmp_path / "env_config.json"
    config_file.write_text(json.dumps(config_data))

    monkeypatch.setenv("PREP_CONFIG", str(config_file))
    result = fresh_prep.initialize()

    assert result == config_data


def test_initialize_caches(tmp_path, fresh_prep):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"a": 1}))
    first = fresh_prep.initialize(str(config_file))

    # Modify the file after initialization; cached value should be returned
    config_file.write_text(json.dumps({"a": 2}))
    second = fresh_prep.initialize()

    assert first == {"a": 1}
    assert second == {"a": 1}


def test_initialize_force_reload(tmp_path, fresh_prep):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"value": 1}))
    fresh_prep.initialize(str(config_file))

    # Update the file and force a reload without specifying the path
    config_file.write_text(json.dumps({"value": 2}))
    reloaded = fresh_prep.initialize(force_reload=True)

    assert reloaded == {"value": 2}
