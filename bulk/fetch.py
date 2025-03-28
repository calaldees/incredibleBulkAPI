import datetime
import http.client
import logging
import typing as t
import urllib.request
from types import MappingProxyType

import aiohttp
import ujson as json

from .cache_tools import DoNotPersistCacheException, cache_disk

log = logging.getLogger(__name__)


type Json = t.Mapping | t.Sequence


@cache_disk(
    ttl=datetime.timedelta(weeks=52)
)  # TODO: can timedelta for cache be configured per site?
async def fetch_url(
    url: str,
    headers: dict[str, str],
    method: str = "GET",
    data: bytes = b"",
) -> bytes:
    # Needs to be sync, because I haven't got a running event-loop right now
    with urllib.request.urlopen(
        urllib.request.Request(url=url, headers=headers, method=method, data=data)
    ) as response:
        return response.read()

    # Broken
    async with aiohttp.ClientSession() as session:
        # breakpoint()   # i can get to here
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=5,
            ssl=False,  # Ignore all SSL certificates
        ) as response:
            breakpoint()  # I cant get to here!? .. wtf?
            if response.status_code != 200:
                log.warning(f"Failed {url=}")
                raise DoNotPersistCacheException(f"failed: {url}")
            return await response.json()


async def fetch_json(
    url: str,
    headers: dict[str, str],
    method: str = "GET",
    data: Json = MappingProxyType({}),
) -> Json:
    return json.loads(
        await fetch_url(
            url=url,
            headers={**headers, "Content-Type": "application/json"},
            method=method,
            data=json.dumps(data),
        )
    )
