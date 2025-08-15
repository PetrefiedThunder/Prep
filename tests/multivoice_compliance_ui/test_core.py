import json
from multivoice_compliance_ui.core import MultiVoiceComplianceUI


def test_load_validate_and_report(tmp_path):
    config = {
        "languages": ["en", "es"],
        "rules": {"greeting": "Must greet in selected language"},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))

    ui = MultiVoiceComplianceUI()
    ui.load_config(str(config_path))
    ui.actions.append({"language": "en", "action": "greet"})

    assert ui.validate() is True

    report = json.loads(ui.generate_report())
    assert report == {
        "total_actions": 1,
        "languages_used": ["en"],
    }
