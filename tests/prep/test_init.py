import json
import prep


def test_initialize(tmp_path):
    config_data = {"option": "value"}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    result = prep.initialize(str(config_file))
    assert result == config_data
