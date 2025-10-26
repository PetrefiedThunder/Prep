"""Download the latest encrypted metrics CSV from S3, decrypt with AWS KMS, and
print the first five rows.

Usage::

    python decrypt_metrics.py --bucket my-metrics-bucket --prefix metrics/

AWS credentials are expected to be configured in the environment (via
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, instance roles, or similar). The
script uses the default AWS region unless overridden by standard boto3
configuration.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from typing import Dict, Iterable

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError


@dataclass
class MetricsObject:
    """Metadata for an encrypted metrics CSV stored in S3."""

    bucket: str
    key: str
    last_modified: object


def parse_encryption_context(
    context_pairs: Iterable[str] | None,
) -> Dict[str, str] | None:
    """Convert ``key=value`` pairs into a dictionary.

    Parameters
    ----------
    context_pairs:
        Iterable of strings formatted as ``key=value``.

    Returns
    -------
    dict | None
        Parsed encryption context dictionary or ``None`` when no pairs are
        provided.
    """

    if not context_pairs:
        return None

    context: Dict[str, str] = {}
    for pair in context_pairs:
        if "=" not in pair:
            raise ValueError(
                f"Invalid encryption context entry '{pair}'. Expected key=value format."
            )
        key, value = pair.split("=", 1)
        context[key] = value
    return context


def find_latest_metrics_object(
    s3_client: BaseClient,
    bucket: str,
    prefix: str | None = None,
) -> MetricsObject:
    """Return the most recently modified object matching the prefix."""

    paginator = s3_client.get_paginator("list_objects_v2")
    pagination_config = {"PageSize": 1000}
    list_kwargs = {"Bucket": bucket, "PaginationConfig": pagination_config}
    if prefix:
        list_kwargs["Prefix"] = prefix

    latest_obj: MetricsObject | None = None

    for page in paginator.paginate(**list_kwargs):
        contents = page.get("Contents", [])
        for obj in contents:
            if not obj.get("Key", "").lower().endswith(".csv"):
                continue
            if latest_obj is None or obj["LastModified"] > latest_obj.last_modified:
                latest_obj = MetricsObject(bucket=bucket, key=obj["Key"], last_modified=obj["LastModified"])

    if latest_obj is None:
        raise FileNotFoundError(
            f"No CSV objects found in bucket '{bucket}' with prefix '{prefix or ''}'."
        )

    return latest_obj


def download_object(s3_client: BaseClient, metrics_object: MetricsObject) -> bytes:
    """Download the encrypted CSV object."""

    response = s3_client.get_object(Bucket=metrics_object.bucket, Key=metrics_object.key)
    return response["Body"].read()


def decrypt_csv(kms_client: BaseClient, ciphertext: bytes, encryption_context: Dict[str, str] | None) -> str:
    """Decrypt ciphertext using AWS KMS and return the decoded CSV text."""

    decrypt_kwargs = {"CiphertextBlob": ciphertext}
    if encryption_context:
        decrypt_kwargs["EncryptionContext"] = encryption_context

    response = kms_client.decrypt(**decrypt_kwargs)
    plaintext = response["Plaintext"]
    if isinstance(plaintext, str):
        return plaintext
    return plaintext.decode("utf-8")


def print_first_rows(csv_text: str, limit: int = 5) -> None:
    """Print the first ``limit`` rows of the CSV to stdout."""

    reader = csv.reader(io.StringIO(csv_text))
    for idx, row in enumerate(reader):
        print(",".join(row))
        if idx + 1 >= limit:
            break


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True, help="S3 bucket that stores encrypted metrics CSV files.")
    parser.add_argument(
        "--prefix",
        default=None,
        help="Optional S3 key prefix used to scope the search for metrics files.",
    )
    parser.add_argument(
        "--encryption-context",
        nargs="*",
        help="Optional key=value pairs defining the KMS encryption context.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=5,
        help="Number of rows to print from the decrypted CSV (default: 5).",
    )

    args = parser.parse_args(argv)

    try:
        encryption_context = parse_encryption_context(args.encryption_context)
        s3_client = boto3.client("s3")
        kms_client = boto3.client("kms")

        latest_metrics = find_latest_metrics_object(s3_client, args.bucket, args.prefix)
        ciphertext = download_object(s3_client, latest_metrics)
        csv_text = decrypt_csv(kms_client, ciphertext, encryption_context)
        print_first_rows(csv_text, args.rows)

        return 0
    except (BotoCoreError, ClientError) as exc:
        print(f"AWS error: {exc}", file=sys.stderr)
    except Exception as exc:  # pragma: no cover - best effort logging of unexpected errors.
        print(f"Error: {exc}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
