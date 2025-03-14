import datetime
from pathlib import Path
from typing import Mapping, Sequence

import aiohttp
import sanic
from sanic.log import logger as log

from ..cache_tools import cache_disk, DoNotPersistCacheException
from .background import setup_background_bulk_generator


@cache_disk(ttl=datetime.timedelta(weeks=52))  # TODO: can timedelta for cache be configured per site?
async def get_url(url: str, headers: dict[str, str]) -> Mapping | Sequence:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status_code != 200:
                log.warning(f"Failed {url=}")
                raise DoNotPersistCacheException(f'failed: {url}')
            return await response.json()


async def _bulk_data(request: sanic.Request) -> sanic.HTTPResponse:
    """
    curl --header "Accept: application/vnd.global.5+json" --url http://localhost:9100/_bulk_data

    Consider Semaphores?
    https://stackoverflow.com/a/70792682/3356840
        sem = asyncio.Semaphore(8)  # no. of simultaneous requests
        async def get_data(client, postdata):
            async with sem:
                res = client.post(url=_url, headers=_headers, data=postdata)
            return res
    or queue?
    https://docs.python.org/3/library/asyncio-queue.html#asyncio.Queue
    """
    #get_url = get_url_func_for_app(request.app)
    cache = {}
    to_crawl: dict = {"/features": 0}
    while to_crawl:
        url, depth = to_crawl.popitem()
        log.info(f"todo={len(to_crawl)} done={len(cache.keys())} {url=}")
        data = await get_url(url, request.headers)
        cache[url] = data
        if "playable_list" in url and depth > 2:
            # `playable_lists`` are all postcasts and episodes - catchup is on a different url -
            # 'playable_list' in url and depth > 2 == gives 582 pages uncompressed6.4mb  gzip0.84mb
            # no depth full 1300 pages uncompressed 32mb gzip 4.2mb
            # depth > 2 - gives 175 uncompressed 5.4mb gzip 0.75mb
            continue
        for url in extract_urls(url, data):
            to_crawl.setdefault(
                url, depth + 1
            )  # BUG: not quite right, we want to replace if depth is lower
        for key in to_crawl.keys() & cache.keys():
            del to_crawl[key]

    # TODO: Bug: the static images don't have the right host
    return sanic.response.json(cache)


def register_bulk_data_generator(app: sanic.Sanic):
    app.ctx.BULK_CACHE_OUTPUT_PATH_DATA = Path("cache_bulk_data.json.gz")
    app.ctx.BULK_CACHE_REGEN_PERIOD = datetime.timedelta(hours=1)
    app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD = datetime.timedelta(seconds=10)

    app.add_route(_bulk_data, "/_bulk_data")
    #app.add_route(bulk_data, "/bulk_data")

    setup_background_bulk_generator(
        app,
        endpoint_path="/_bulk_data",
        output_path=app.ctx.BULK_CACHE_OUTPUT_PATH_DATA,
        cache_period=app.ctx.BULK_CACHE_REGEN_PERIOD,
        retry_period=app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD,
        headers={"Accept": "application/vnd.global.5+json"},
    )
