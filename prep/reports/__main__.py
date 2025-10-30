"""CLI entrypoint for compliance report generation."""

from __future__ import annotations

import asyncio

from .compliance import generate_compliance_manifest


def main() -> None:  # pragma: no cover - CLI helper
    path = asyncio.run(generate_compliance_manifest())
    print(f"Compliance manifest generated at {path}")


if __name__ == "__main__":
    main()
