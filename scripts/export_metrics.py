"""Export host metrics to CSV and upload to S3 with KMS encryption."""
from __future__ import annotations

import csv
import io
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Iterator, Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Result
from sqlalchemy.exc import SQLAlchemyError


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
BUCKET_NAME = "investor-data-room"
S3_OBJECT_KEY_TEMPLATE = "metrics_{date}.csv"
KMS_KEY_ALIAS = "alias/investor-room"


class MetricsExportError(RuntimeError):
    """Raised when exporting metrics fails."""


@contextmanager
def db_connection(database_url: str) -> Iterator[Connection]:
    """Yield a SQLAlchemy connection."""
    engine: Engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


def fetch_metrics(connection: Connection) -> Result:
    """Fetch all rows from the mv_host_metrics materialized view."""
    return connection.execute(text("SELECT * FROM mv_host_metrics"))


def render_csv(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    """Serialize rows to CSV returning UTF-8 encoded bytes."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue().encode("utf-8")


def upload_to_s3(data: bytes, *, bucket: str, key: str) -> None:
    """Upload the provided data to the specified S3 location with KMS encryption."""
    s3_client = boto3.client("s3")
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="text/csv",
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=KMS_KEY_ALIAS,
        )
    except (BotoCoreError, ClientError) as exc:
        raise MetricsExportError("Failed to upload metrics to S3") from exc


def main() -> None:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    export_date = datetime.utcnow().date().isoformat()
    s3_key = S3_OBJECT_KEY_TEMPLATE.format(date=export_date)

    try:
        with db_connection(database_url) as connection:
            result = fetch_metrics(connection)
            csv_bytes = render_csv(result.keys(), result.fetchall())
    except SQLAlchemyError as exc:
        raise MetricsExportError("Failed to retrieve metrics from the database") from exc

    upload_to_s3(csv_bytes, bucket=BUCKET_NAME, key=s3_key)


if __name__ == "__main__":
    main()
