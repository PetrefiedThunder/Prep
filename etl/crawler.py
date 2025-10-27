"""Async crawler that fetches regulatory documents into raw S3 storage."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Iterable, Sequence
from urllib.parse import unquote, urlsplit

import aiohttp
import boto3
from aiohttp import ClientError

logger = logging.getLogger(__name__)

DEFAULT_BUCKET = "prep-etl-raw"
MAX_ATTEMPTS = 5


@dataclass(slots=True)
class FetchResult:
    """Record of a processed URL."""

    url: str
    key: str | None
    sha256: str | None
    error: Exception | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def _extract_jurisdiction(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    if not path:
        return "unknown"
    first = path.split("/")[0]
    return first.lower() or "unknown"


def _extract_filename(url: str) -> str:
    path = urlsplit(url).path
    name = PurePosixPath(path).name
    if not name:
        name = urlsplit(url).netloc.replace(":", "_") or "index.html"
    return unquote(name)


async def _store_in_s3(
    *,
    s3_client,
    bucket: str,
    key: str,
    body: bytes,
    sha256_hash: str,
) -> None:
    """Persist the payload to S3 using a background thread."""

    metadata = {"sha256": sha256_hash}
    await asyncio.to_thread(
        s3_client.put_object, Bucket=bucket, Key=key, Body=body, Metadata=metadata
    )


async def fetch_and_store(
    url: str,
    *,
    session: aiohttp.ClientSession,
    s3_client,
    bucket: str = DEFAULT_BUCKET,
    run_date: datetime | None = None,
    max_attempts: int = MAX_ATTEMPTS,
    sleep: callable = asyncio.sleep,
) -> FetchResult:
    """Fetch ``url`` with retries and persist to S3."""

    attempts = 0
    backoff = 1
    run_date = run_date or datetime.now(UTC)

    while True:
        attempts += 1
        try:
            async with session.get(url) as response:
                if 500 <= response.status < 600:
                    if attempts >= max_attempts:
                        body = await response.read()
                        msg = f"Server error {response.status} after {attempts} attempts"
                        return FetchResult(url, None, None, RuntimeError(msg))
                    logger.debug("5xx response for %s, retrying", url)
                    await sleep(backoff)
                    backoff *= 2
                    continue

                response.raise_for_status()
                body = await response.read()
        except ClientError as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            return FetchResult(url, None, None, exc)
        break

    digest = hashlib.sha256(body).hexdigest()
    jurisdiction = _extract_jurisdiction(url)
    filename = _extract_filename(url)
    key = f"{run_date.strftime('%Y-%m-%d')}/{jurisdiction}/{filename}"

    try:
        await _store_in_s3(s3_client=s3_client, bucket=bucket, key=key, body=body, sha256_hash=digest)
    except Exception as exc:  # pragma: no cover - boto3 exceptions vary heavily
        logger.exception("Failed to store %s in S3", url)
        return FetchResult(url, None, None, exc)

    return FetchResult(url, key, digest)


async def process_urls(
    urls: Sequence[str],
    *,
    bucket: str = DEFAULT_BUCKET,
    run_date: datetime | None = None,
    session: aiohttp.ClientSession | None = None,
    s3_client=None,
    sleep: callable = asyncio.sleep,
) -> dict[str, int]:
    """Process a batch of URLs and return a summary."""

    if not urls:
        return {"success": 0, "failed": 0}

    run_date = run_date or datetime.now(UTC)
    owns_session = session is None
    session = session or aiohttp.ClientSession()
    s3_client = s3_client or boto3.client("s3")

    try:
        tasks = [
            fetch_and_store(
                url,
                session=session,
                s3_client=s3_client,
                bucket=bucket,
                run_date=run_date,
                sleep=sleep,
            )
            for url in urls
        ]
        results = await asyncio.gather(*tasks)
    finally:
        if owns_session:
            await session.close()

    summary = {"success": 0, "failed": 0}
    for result in results:
        if result.success:
            summary["success"] += 1
        else:
            summary["failed"] += 1
            logger.error("Failed to process %s: %s", result.url, result.error)
    return summary


def _read_urls_from_stdin(stdin: Iterable[str]) -> list[str]:
    return [line.strip() for line in stdin if line.strip()]


def main() -> None:
    """Entry point for CLI usage."""

    urls = _read_urls_from_stdin(sys.stdin)
    if not urls:
        logger.info("No URLs provided to crawler")
        return
    summary = asyncio.run(process_urls(urls))
    logger.info("Crawler finished: %s", summary)


if __name__ == "__main__":  # pragma: no cover
    main()
