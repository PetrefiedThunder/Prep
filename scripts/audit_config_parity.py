"""Audit parity between San Francisco compliance config and validators."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Sequence, Set

try:
    import yaml
except ImportError:  # pragma: no cover - handled in tests
    yaml = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "regengine" / "cities" / "san_francisco" / "config.yaml"
DEFAULT_SERVICES_PATH = (
    REPO_ROOT
    / "apps"
    / "sf_regulatory_service"
    / "services.py"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "audits" / "structural" / "SF_Config_Parity_Report.json"


class AuditError(RuntimeError):
    """Raised when the audit cannot be executed."""


def _relativize(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that every San Francisco compliance rule defined in the config "
            "has a corresponding validator and that validators do not request missing keys."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the San Francisco compliance config YAML file.",
    )
    parser.add_argument(
        "--services",
        type=Path,
        default=DEFAULT_SERVICES_PATH,
        help="Path to the San Francisco regulatory services module.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination path for the generated JSON audit report.",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Return a non-zero exit code when parity issues are detected.",
    )
    return parser.parse_args(argv)


def _parse_compliance_keys_fallback(text: str) -> Set[str]:
    """Extract compliance keys without a YAML parser."""

    compliance_indent: int | None = None
    key_indent: int | None = None
    collecting = False
    keys: Set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(stripped)

        if not collecting:
            if stripped.startswith("compliance") and stripped.split(":", 1)[0] == "compliance":
                compliance_indent = indent
                collecting = True
            continue

        if compliance_indent is not None and indent <= compliance_indent:
            break

        if stripped.startswith("-"):
            continue

        if ":" not in stripped:
            continue

        if key_indent is None:
            key_indent = indent

        if indent != key_indent:
            continue

        key = stripped.split(":", 1)[0].strip()
        if key:
            keys.add(key)

    return keys


def load_compliance_keys(config_path: Path) -> Set[str]:
    text = config_path.read_text(encoding="utf-8")
    if yaml is None:
        return _parse_compliance_keys_fallback(text)

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise AuditError(f"Unexpected config schema in {config_path}")
    compliance = data.get("compliance", {})
    if compliance is None:
        return set()
    if not isinstance(compliance, dict):
        raise AuditError("The `compliance` section must be a mapping")
    keys = {str(key) for key in compliance.keys()}
    return keys


_CONFIG_PATTERN = re.compile(r"\b(?:self\.)?config\.get\(\s*['\"]([^'\"]+)['\"]")


def discover_validator_keys(services_path: Path) -> Set[str]:
    text = services_path.read_text(encoding="utf-8")
    matches = _CONFIG_PATTERN.findall(text)
    return {match for match in matches}


def build_report(
    *,
    config_path: Path,
    service_path: Path,
    config_keys: Iterable[str],
    validator_keys: Iterable[str],
) -> Dict[str, object]:
    config_key_set = set(config_keys)
    validator_key_set = set(validator_keys)
    unused_keys = sorted(config_key_set - validator_key_set)
    missing_validators = sorted(validator_key_set - config_key_set)
    parity = not unused_keys and not missing_validators
    status = "pass" if parity else "fail"
    summary = (
        "All compliance config rules have matching validators."
        if parity
        else "Config rules and validators are out of parity."
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    report: Dict[str, object] = {
        "audit": "sf_config_parity",
        "generated_at": generated_at,
        "config_path": _relativize(config_path),
        "services_path": _relativize(service_path),
        "status": status,
        "summary": summary,
        "config_keys": sorted(config_key_set),
        "validator_keys": sorted(validator_key_set),
        "unused_config_keys": unused_keys,
        "missing_validators": missing_validators,
        "issue_count": len(unused_keys) + len(missing_validators),
    }
    return report


def write_report(report: Dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config_keys = load_compliance_keys(args.config)
        validator_keys = discover_validator_keys(args.services)
        report = build_report(
            config_path=args.config,
            service_path=args.services,
            config_keys=config_keys,
            validator_keys=validator_keys,
        )
        write_report(report, args.output)
    except AuditError as exc:  # pragma: no cover - defensive logging path
        print(f"Audit failed: {exc}")
        return 2

    if args.fail_on_issues and report["issue_count"]:
        return 1

    if report["issue_count"]:
        print("Config parity issues detected. See report:", args.output)
    else:
        print("Config parity audit succeeded. Report:", args.output)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
