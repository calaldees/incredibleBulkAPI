import datetime
from pathlib import Path
from typing import Mapping, Sequence

import sanic
from sanic.log import logger as log

from guacamole.features.data import get_path

from . import crawl_for_key, get_url_func_for_app, setup_background_bulk_generator


def extract_urls(current_path: str, data: Mapping | Sequence) -> set[str]:
    """
    >>> extract_urls(None, {})
    set()
    >>> extract_urls(
    ...     None,
    ...     [
    ...         1,
    ...         2,
    ...         {'primary_action': 'NotRightType'},
    ...         {'primary_action': {'payload': {'link': {'href': 'fake_url'}}}},
    ...     ],
    ... )
    {'fake_url'}
    """
    # Features - is a list of items
    if get_path(data, '0.slug'):
        return {f"{current_path}/{i.get('slug')}" for i in data}
    # CarPage - crawl for primary_action navigate hrefs
    car_page_navigate_hrefs: set[str] = set(
        filter(
            None,
            (
                get_path(primary_action, 'payload.link.href')  # type: ignore
                for primary_action in crawl_for_key(data, 'primary_action')
            ),
        )
    )
    # set(
    # TODO: cache Playables
    # get_path(primary_action, 'payload.id')
    # Although these are calls to `bff-mobile` and may need more client work
    # )
    return car_page_navigate_hrefs


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
    get_url = get_url_func_for_app(request.app)
    cache = {}
    to_crawl: dict = {'/features': 0}
    while to_crawl:
        url, depth = to_crawl.popitem()
        log.info(f'todo={len(to_crawl)} done={len(cache.keys())} {url=}')
        data = await get_url(url, request.headers)
        cache[url] = data
        if 'playable_list' in url and depth > 2:
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


async def bulk_data(request: sanic.Request) -> sanic.HTTPResponse:
    """
    curl --compressed --header "Accept: application/vnd.global.5+json" --url http://localhost:9100/bulk_data
    """
    if 'gzip' not in request.headers.get('Accept-Encoding', ''):
        raise sanic.exceptions.BadRequest('gzip encoding is required')
    cache_period = request.app.ctx.BULK_CACHE_REGEN_PERIOD
    path = request.app.ctx.BULK_CACHE_OUTPUT_PATH_DATA
    if not path.exists():
        # 307 - TEMPORARY REDIRECT - https://stackoverflow.com/a/12281287/3356840
        return sanic.response.redirect(
            request.path, status=307, headers={'Retry-After': 360}
        )
    age: datetime.timedelta = datetime.datetime.now() - datetime.datetime.fromtimestamp(path.stat().st_mtime)
    # To prevent middleware exception - add this to
    # /usr/local/lib/python3.12/site-packages/sanic_compress/__init__.py
    #    _compressed_response
    #       if (not hasattr(response, 'body')):
    #        return response
    return await sanic.response.file_stream(
        path,
        headers={
            'Cache-Control': f'max-age={int((cache_period - age).total_seconds())}',
            'Age': f'{int(age.total_seconds())}',
            'Content-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'Content-Length': str(path.stat().st_size),
        },
    )


def register_bulk_data_generator(app: sanic.Sanic):
    app.ctx.BULK_CACHE_OUTPUT_PATH_DATA = Path('cache_bulk_data.json.gz')
    app.ctx.BULK_CACHE_REGEN_PERIOD = datetime.timedelta(hours=1)
    app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD = datetime.timedelta(seconds=10)

    app.add_route(_bulk_data, '/_bulk_data')
    app.add_route(bulk_data, '/bulk_data')

    setup_background_bulk_generator(
        app,
        endpoint_path='/_bulk_data',
        output_path=app.ctx.BULK_CACHE_OUTPUT_PATH_DATA,
        cache_period=app.ctx.BULK_CACHE_REGEN_PERIOD,
        retry_period=app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD,
        headers={'Accept': 'application/vnd.global.5+json'},
    )
