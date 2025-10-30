#!/usr/bin/env python3
"""Validate core build artefacts for the CI/CD pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REQUIRED_DOCKERFILES = [
    "Dockerfile",
    "Dockerfile.compliance",
    "Dockerfile.reports",
    "Dockerfile.regression",
]


def _run_command(command: list[str]) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    missing = [path for path in REQUIRED_DOCKERFILES if not (project_root / path).exists()]
    if missing:
        raise SystemExit(f"Missing required Dockerfiles: {', '.join(missing)}")

    helm_chart = project_root / "helm" / "prepchef"
    if not helm_chart.exists():
        raise SystemExit("Helm chart directory helm/prepchef is missing")

    _run_command(["helm", "template", "prepchef", str(helm_chart)])


if __name__ == "__main__":  # pragma: no cover - CLI utility
    main()
