"""Asynchronous crawler that uploads fetched documents to S3.

The crawler reads lines from standard input where each non-empty line defines a
jurisdiction and the URL to fetch. Lines can be comma, tab, or whitespace
separated, for example::

    ca,https://example.com/regulations
    ny https://example.com/other.pdf

Fetched documents are uploaded to the ``prep-etl-raw`` bucket with an
``sha256`` metadata entry. Errors are surfaced via logging and result in a
non-zero exit status.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import hashlib
import logging
import os
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Sequence, Tuple

import aiohttp
import boto3

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
                    continue

                response.raise_for_status()
                body = await response.read()
                logger.debug("Fetched %s (%d bytes)", url, len(body))
                return body
        except aiohttp.ClientError as exc:
            if attempt >= max_attempts:
                logger.error("Failed to fetch %s after %d attempts", url, attempt)
                raise CrawlerError(f"Failed to fetch {url}") from exc
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "Client error %s for %s (attempt %s/%s); retrying in %.2fs",
                exc,
                url,
                attempt,
                max_attempts,
                delay,
            )
            await sleep(delay)


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

    parsed = urllib.parse.urlparse(url)
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
        date_prefix = _dt.datetime.utcnow().date().isoformat()

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
