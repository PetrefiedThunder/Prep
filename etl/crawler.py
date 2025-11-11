"""Async crawler that fetches regulatory documents into raw S3 storage."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse, urlsplit

import aiohttp
import boto3
from aiohttp import ClientError

logger = logging.getLogger(__name__)

DEFAULT_BUCKET = "prep-etl-raw"
DEFAULT_CONCURRENCY = 5
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BASE_DELAY = 0.5
DEFAULT_MAX_DELAY = 8.0


@dataclass(frozen=True)
class CrawlTarget:
    """Represents a single jurisdiction URL to crawl."""

    jurisdiction: str
    url: str


class CrawlerError(RuntimeError):
    """Raised when the crawler fails to process a URL."""


async def fetch_with_backoff(
    session: aiohttp.ClientSession,
    url: str,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bytes:
    """Fetch ``url`` retrying with exponential backoff on transient failures.

    Parameters
    ----------
    session:
        The :class:`aiohttp.ClientSession` used to make HTTP requests.
    url:
        The HTTP(s) URL to download.
    max_attempts:
        Maximum number of attempts, including the initial request.
    base_delay:
        Initial delay in seconds for the backoff sequence.
    max_delay:
        Maximum delay applied between retries.
    sleep:
        Awaitable sleep function used to delay between retries. The default
        is :func:`asyncio.sleep`, but a custom implementation can be provided
        for testing.
    """

    attempt = 0
    while True:
        attempt += 1
        try:
            async with session.get(url) as response:
                if 500 <= response.status < 600:
                    if attempt >= max_attempts:
                        response.raise_for_status()
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "HTTP %s for %s (attempt %s/%s); retrying in %.2fs",
                        response.status,
                        url,
                        attempt,
                        max_attempts,
                        delay,
                    )
                    await sleep(delay)
                    continue  # Retry

                # Success case - return content
                response.raise_for_status()  # Raise for 4xx errors
                return await response.read()

        except ClientError as exc:
            if attempt >= max_attempts:
                raise CrawlerError(f"Failed to fetch {url} after {max_attempts} attempts") from exc
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning("Client error for %s (attempt %s/%s); retrying in %.2fs", url, attempt, max_attempts, delay)
            await sleep(delay)


# Constants defined at module level
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
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> FetchResult:
    """Fetch ``url`` with retries and persist to S3."""

    attempts = 0
    run_date = run_date or datetime.now(UTC)

    while attempts < max_attempts:
        attempts += 1
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if 500 <= response.status < 600:
                    if attempts >= max_attempts:
                        msg = f"Server error {response.status} after {attempts} attempts"
                        return FetchResult(url, None, None, RuntimeError(msg))
                    delay = min(base_delay * (2 ** (attempts - 1)), max_delay)
                    logger.debug("5xx response for %s, retrying in %.2fs", url, delay)
                    await sleep(delay)
                    continue

                response.raise_for_status()
                body = await response.read()

                # Calculate hash and store in S3
                sha256_hash = hashlib.sha256(body).hexdigest()
                jurisdiction = _extract_jurisdiction(url)
                filename = _extract_filename(url)
                key = f"{run_date.date().isoformat()}/{jurisdiction}/{filename}"

                await _store_in_s3(
                    s3_client=s3_client,
                    bucket=bucket,
                    key=key,
                    body=body,
                    sha256_hash=sha256_hash,
                )

                logger.info("Stored %s (%d bytes) to s3://%s/%s", url, len(body), bucket, key)
                return FetchResult(url, key, sha256_hash, None)

        except aiohttp.ClientError as exc:
            if attempts >= max_attempts:
                logger.error("Failed to fetch %s after %d attempts: %s", url, attempts, exc)
                return FetchResult(url, None, None, exc)

            delay = min(base_delay * (2 ** (attempts - 1)), max_delay)
            logger.warning(
                "Client error for %s (attempt %d/%d); retrying in %.2fs: %s",
                url,
                attempts,
                max_attempts,
                delay,
                exc,
            )
            await sleep(delay)

        except Exception as exc:
            logger.error("Unexpected error fetching %s: %s", url, exc, exc_info=True)
            return FetchResult(url, None, None, exc)

    # Should never reach here
    return FetchResult(url, None, None, RuntimeError(f"Max attempts ({max_attempts}) exceeded"))


def parse_targets(lines: Iterable[str]) -> List[CrawlTarget]:
    """Parse jurisdiction/URL pairs from ``lines``.

    Lines starting with ``#`` or blank lines are ignored. Each remaining line
    must contain a jurisdiction and a URL separated by a comma, tab, or
    whitespace.
    """

    targets: List[CrawlTarget] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        jurisdiction: Optional[str]
        url: Optional[str] = None
        if "," in line:
            jurisdiction, url = [part.strip() for part in line.split(",", 1)]
        elif "\t" in line:
            jurisdiction, url = [part.strip() for part in line.split("\t", 1)]
        else:
            parts = line.split()
            if len(parts) < 2:
                raise ValueError(f"Invalid input line: '{line}'")
            jurisdiction, url = parts[0], parts[1]

        if not jurisdiction or not url:
            raise ValueError(f"Invalid input line: '{line}'")

        targets.append(CrawlTarget(jurisdiction=jurisdiction, url=url))

    return targets


def build_s3_key(date_prefix: str, jurisdiction: str, url: str) -> str:
    """Construct the S3 key for ``url`` within ``jurisdiction``."""

    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if not filename:
        filename = "index.html"
    return f"{date_prefix}/{jurisdiction}/{filename}"


async def fetch_and_upload(
    session: aiohttp.ClientSession,
    s3_client,
    target: CrawlTarget,
    *,
    bucket: str,
    date_prefix: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    to_thread: Callable[..., Awaitable[Any]] = asyncio.to_thread,
) -> Tuple[str, str]:
    """Fetch ``target`` and upload to S3.

    Returns a tuple of the S3 key and the SHA-256 hex digest.
    """

    body = await fetch_with_backoff(
        session,
        target.url,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        sleep=sleep,
    )

    digest = hashlib.sha256(body).hexdigest()
    key = build_s3_key(date_prefix, target.jurisdiction, target.url)
    metadata = {"sha256": digest}

    await to_thread(
        s3_client.put_object,
        Bucket=bucket,
        Key=key,
        Body=body,
        Metadata=metadata,
    )

    logger.info("Uploaded %s to s3://%s/%s", target.url, bucket, key)
    return key, digest


async def run_crawler(
    targets: Sequence[CrawlTarget],
    *,
    bucket: str = DEFAULT_BUCKET,
    concurrency: int = DEFAULT_CONCURRENCY,
    date_prefix: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
    s3_client=None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Run the crawler for the provided ``targets``."""

    if not targets:
        logger.info("No targets provided; nothing to do")
        return

    own_session = session is None
    own_s3_client = s3_client is None
    if date_prefix is None:
        date_prefix = datetime.now(UTC).date().isoformat()

    if own_s3_client:
        s3_client = boto3.client("s3")

    if own_session:
        timeout = aiohttp.ClientTimeout(total=None)
        connector = aiohttp.TCPConnector(limit=concurrency * 2)
        session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    assert session is not None
    assert s3_client is not None

    semaphore = asyncio.Semaphore(concurrency)

    async def worker(target: CrawlTarget) -> None:
        async with semaphore:
            await fetch_and_upload(
                session,
                s3_client,
                target,
                bucket=bucket,
                date_prefix=date_prefix,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                sleep=sleep,
            )

    try:
        await asyncio.gather(*(worker(target) for target in targets))
    finally:
        if own_session:
            await session.close()
        if own_s3_client:
            s3_client.close()


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch URLs and upload to S3")
    parser.add_argument(
        "--bucket",
        default=os.getenv("CRAWLER_BUCKET", DEFAULT_BUCKET),
        help="Destination S3 bucket",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("CRAWLER_CONCURRENCY", DEFAULT_CONCURRENCY)),
        help="Maximum concurrent requests",
    )
    parser.add_argument(
        "--date",
        default=os.getenv("CRAWLER_DATE"),
        help="Explicit date prefix (defaults to UTC today)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (can be supplied multiple times)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    configure_logging(args.verbose)

    try:
        targets = parse_targets(sys.stdin)
    except ValueError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc

    if not targets:
        logger.info("No URLs provided on stdin")
        return

    try:
        asyncio.run(
            run_crawler(
                targets,
                bucket=args.bucket,
                concurrency=args.concurrency,
                date_prefix=args.date,
            )
        )
    except CrawlerError as exc:
        logger.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()


async def process_urls(
    urls: Sequence[str],
    *,
    bucket: str = DEFAULT_BUCKET,
    run_date: datetime | None = None,
    session: aiohttp.ClientSession | None = None,
    s3_client=None,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    max_attempts: int = MAX_ATTEMPTS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
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
                base_delay=base_delay,
                max_delay=max_delay,
                max_attempts=max_attempts,
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
