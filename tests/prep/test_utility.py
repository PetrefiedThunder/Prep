"""Tests for ``prep.utility`` functions."""

import json

import pytest

from prep import utility


def test_util_func_loads_json(tmp_path):
    """The utility correctly loads JSON configuration files."""
    data = {"a": 1}
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(data))
    assert utility.util_func(cfg) == data


def test_util_func_missing_file(tmp_path):
    """A missing file results in ``FileNotFoundError``."""
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        utility.util_func(missing)


def test_util_func_invalid_json(tmp_path):
    """Malformed JSON raises ``JSONDecodeError``."""
    cfg = tmp_path / "bad.json"
    cfg.write_text("{bad json}")
    with pytest.raises(json.JSONDecodeError):
        utility.util_func(cfg)
