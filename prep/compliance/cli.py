from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .config import ComplianceConfigManager
from .coordinator import ComplianceCoordinator


def _load_data(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}
    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prep Compliance Engine")
    parser.add_argument("--audit", action="store_true", help="Run comprehensive compliance audit")
    parser.add_argument("--data", type=str, help="Path to JSON data file")
    parser.add_argument("--config", type=str, default="config/compliance.yaml", help="Path to config file")
    parser.add_argument("--output", type=str, default="compliance_report.json", help="Output file path")
    args = parser.parse_args()

    config_manager = ComplianceConfigManager(args.config)
    config = config_manager.config  # ensure config loaded

    data = _load_data(args.data)

    if args.audit:
        enabled_engines = getattr(config, "enabled_engines", None) if config else None
        coordinator = ComplianceCoordinator(enabled_engines=enabled_engines)
        reports = coordinator.run_comprehensive_audit(data)
        summary = coordinator.generate_executive_summary(reports)
        recommendations = coordinator.get_priority_recommendations(reports)

        output_payload = {
            "timestamp": datetime.now().isoformat(),
            "executive_summary": summary,
            "priority_recommendations": recommendations,
            "detailed_reports": {
                name: {
                    "engine_name": report.engine_name,
                    "timestamp": report.timestamp.isoformat(),
                    "total_rules_checked": report.total_rules_checked,
                    "violations_found": len(report.violations_found),
                    "passed_rules": len(report.passed_rules),
                    "summary": report.summary,
                    "overall_compliance_score": report.overall_compliance_score,
                }
                for name, report in reports.items()
            },
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(output_payload, handle, indent=2)

        print(f"Compliance audit completed. Results saved to {output_path}")
        print("\nEXECUTIVE SUMMARY:")
        print(summary)
        print("\nPRIORITY RECOMMENDATIONS:")
        for recommendation in recommendations[:5]:
            print(f"- {recommendation}")


if __name__ == "__main__":
    main()
