from __future__ import annotations

import json
import sys
from textwrap import dedent

from prep.compliance import cli


def test_cli_respects_enabled_engines(tmp_path, monkeypatch) -> None:
    config_content = dedent(
        """
        enabled_engines:
          - dol
          - privacy
        audit_frequency: weekly
        notification_threshold: 0.8
        report_format: json
        storage_path: ./compliance_reports
        retention_days: 90
        enable_simulations: true
        """
    ).strip()

    config_path = tmp_path / "compliance.yaml"
    config_path.write_text(config_content, encoding="utf-8")

    data_path = tmp_path / "data.json"
    data_path.write_text("{}", encoding="utf-8")

    output_path = tmp_path / "result.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prep-compliance",
            "--audit",
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--data",
            str(data_path),
        ],
    )

    cli.main()

    result = json.loads(output_path.read_text(encoding="utf-8"))

    assert set(result["detailed_reports"].keys()) == {"dol", "privacy"}
