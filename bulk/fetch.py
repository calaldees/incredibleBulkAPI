import datetime
import logging
import typing as t

import aiohttp

from .cache_tools import DoNotPersistCacheException, cache_disk

log = logging.getLogger(__name__)


@cache_disk(
    ttl=datetime.timedelta(weeks=52)
)  # TODO: can timedelta for cache be configured per site?
async def get_url(url: str, headers: dict[str, str]) -> t.Mapping | t.Sequence:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status_code != 200:
                log.warning(f"Failed {url=}")
                raise DoNotPersistCacheException(f"failed: {url}")
            return await response.json()
