"""Generate and distribute the San Francisco compliance audit summary."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx

from prep.sf_audit.reporting import (
    build_audit_report,
    build_slack_payload,
    load_pytest_report,
    write_audit_report,
)
from prep.storage.secure_s3 import DEFAULT_KMS_ALIAS, upload_encrypted_json


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish the SF audit summary report")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/sf_audit.json"),
        help="Path to the pytest-json-report artifact",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directory where the condensed audit report should be written",
    )
    parser.add_argument(
        "--s3-bucket", type=str, default=None, help="Optional S3 bucket for archival"
    )
    parser.add_argument(
        "--s3-key", type=str, default=None, help="Optional S3 key for archival upload"
    )
    parser.add_argument(
        "--kms-alias",
        type=str,
        default=DEFAULT_KMS_ALIAS,
        help="KMS alias for server-side encryption when uploading to S3",
    )
    return parser.parse_args(argv)


def _render_output_path(output_dir: Path) -> Path:
    today = datetime.now(tz=UTC).date().isoformat()
    return output_dir / f"SF_Audit_Report_{today}.json"


def _post_to_slack(payload: dict[str, object]) -> None:
    webhook = os.getenv("SLACK_WEBHOOK_SFOPS")
    if not webhook:
        return
    try:
        response = httpx.post(webhook, json=payload, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network failures are surfaced in logs
        raise RuntimeError("Failed to post audit summary to Slack") from exc


def main(argv: Sequence[str] | None = None) -> Path:
    args = _parse_args(argv)
    report_data = load_pytest_report(args.report)
    audit_report = build_audit_report(report_data)
    output_path = _render_output_path(args.output_dir)
    write_audit_report(audit_report, output_path)

    slack_payload = build_slack_payload(audit_report)
    _post_to_slack(slack_payload)

    if args.s3_bucket and args.s3_key:
        upload_encrypted_json(
            audit_report,
            bucket=args.s3_bucket,
            key=args.s3_key,
            kms_alias=args.kms_alias,
        )

    return output_path


if __name__ == "__main__":  # pragma: no cover - manual execution entrypoint
    main()
