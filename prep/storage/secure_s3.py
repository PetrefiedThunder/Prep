"""Helpers for uploading encrypted artifacts to S3."""

from __future__ import annotations

import json
from typing import Any

import boto3


DEFAULT_KMS_ALIAS = "alias/prep-regulatory-artifacts"


def upload_encrypted_json(
    payload: dict[str, Any],
    *,
    bucket: str,
    key: str,
    kms_alias: str = DEFAULT_KMS_ALIAS,
    s3_client: Any | None = None,
) -> Any:
    """Upload ``payload`` to S3 enforcing server-side encryption."""

    client = s3_client or boto3.client("s3")
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    return client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId=kms_alias,
    )


__all__ = ["upload_encrypted_json", "DEFAULT_KMS_ALIAS"]
