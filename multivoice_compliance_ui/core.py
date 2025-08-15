import json
from pathlib import Path
from typing import Dict, List


class MultiVoiceComplianceUI:
    """User interface for multi-language compliance workflows."""

    def __init__(self) -> None:
        self.config: Dict[str, object] = {}
        self.actions: List[Dict[str, str]] = []

    def load_config(self, config_path: str) -> None:
        """Load UI configuration parameters.

        Parameters
        ----------
        config_path:
            Path to a JSON configuration file containing the keys
            ``languages`` (list of supported language codes) and
            ``rules`` (a mapping of rule names to descriptions).
        """

        with Path(config_path).open("r", encoding="utf-8") as fh:
            self.config = json.load(fh)

    def validate(self) -> bool:
        """Validate user actions for compliance.

        The configuration must be loaded and contain ``languages`` and
        ``rules`` keys. Each recorded action must specify a ``language``
        that exists in the configuration.
        """

        required_keys = {"languages", "rules"}
        if not required_keys.issubset(self.config):
            missing = required_keys - self.config.keys()
            raise ValueError(f"Missing config keys: {missing}")

        for action in self.actions:
            language = action.get("language")
            if language not in self.config["languages"]:
                raise ValueError(f"Unsupported language: {language}")

        return True

    def generate_report(self) -> str:
        """Generate user compliance interaction reports.

        Returns
        -------
        str
            JSON string summarising the session including the number of
            actions recorded and the languages used.
        """

        languages_used = {a.get("language") for a in self.actions}
        report = {
            "total_actions": len(self.actions),
            "languages_used": sorted(languages_used),
        }
        return json.dumps(report)
