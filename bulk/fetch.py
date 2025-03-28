import datetime
import logging
import typing as t

import aiohttp
import urllib
import ujson as json

from .cache_tools import DoNotPersistCacheException, cache_disk

log = logging.getLogger(__name__)


@cache_disk(
    ttl=datetime.timedelta(weeks=52)
)  # TODO: can timedelta for cache be configured per site?
async def get_url(url: str, headers: dict[str, str]) -> t.Mapping | t.Sequence:
    return json.load(urllib.request.urlopen(urllib.request.Request(url=url, headers=headers)))

    async with aiohttp.ClientSession() as session:
        #breakpoint()   # i can get to here
        async with session.request(
            method='GET',
            url=url,
            headers=headers,
            timeout=5,
            ssl=False,  # Ignore all SSL certificates
        ) as response:
            breakpoint()   # I cant get to here!? .. wtf?
            if response.status_code != 200:
                log.warning(f"Failed {url=}")
                raise DoNotPersistCacheException(f"failed: {url}")
            return await response.json()
