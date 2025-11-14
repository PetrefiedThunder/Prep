import asyncio
import sys
from collections.abc import Iterable

import aiohttp


async def fetch_status(session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
    try:
        async with session.get(url) as response:
            return url, str(response.status)
    except Exception as exc:  # pylint: disable=broad-except
        return url, f"error: {exc}"


async def fetch_all(urls: Iterable[str]) -> Iterable[tuple[str, str]]:
    timeout = aiohttp.ClientTimeout(total=None)
    connector = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [asyncio.create_task(fetch_status(session, url)) for url in urls]
        return await asyncio.gather(*tasks)


def read_urls() -> Iterable[str]:
    return [line.strip() for line in sys.stdin if line.strip()]


async def async_main() -> None:
    urls = read_urls()
    if not urls:
        return

    results = await fetch_all(urls)
    for url, status in results:
        print(f"{url} {status}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
