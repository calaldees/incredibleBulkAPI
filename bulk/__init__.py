import asyncio
import datetime
import gzip
import itertools
from pathlib import Path
from typing import Mapping, Sequence

import sanic
from sanic.log import logger as log

from .cache_tools import cache_disk


def get_url_func_for_app(app):  # : sanic.Sanic
    @cache_disk(ttl=datetime.timedelta(weeks=52))
    async def get_url(url: str, headers: dict) -> Mapping | Sequence:
        try:
            _, response = await app.asgi_client.get(url, headers=headers)
        except Exception as e:
            log.exception(e)
        if not response or response.status_code != 200:
            log.warning(f'Failed {url=}')
            return {}
        return response.json

    return get_url


def crawl_for_key(data: Mapping | Sequence, key):
    """
    >>> data = {'primary_action': 'hello'}
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ('hello',)

    >>> data = [1, 2, {'primary_action': 'hello'}]
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ('hello',)

    >>> data = {'a': 1, 'b': {'primary_action': 'hello'}}
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ('hello',)

    >>> data = {
    ...     'title': 'Live Radio',
    ...     'sections': [
    ...         {
    ...             'content': [
    ...                 {
    ...                     'id': '',
    ...                     'title': '',
    ...                     'type': 'grid',
    ...                     'items': [
    ...                         {
    ...                             'type': 'item',
    ...                             'id': '42Kuap',
    ...                             'image': {
    ...                                 'url': 'fake',
    ...                                 'shape': 'square',
    ...                             },
    ...                             'title': 'The Trial',
    ...                             'primary_action': {
    ...                                 'type': 'navigate',
    ...                                 'payload': {
    ...                                     'link': {
    ...                                         'type': 'item_list',
    ...                                         'href': '/v1/playable_list/42Kuap',
    ...                                     },
    ...                                 },
    ...                             },
    ...                             enabled: 'true',
    ...                         },
    ...                     ],
    ...                     'primary_action': {
    ...                         'type': 'navigate',
    ...                         'payload': {
    ...                             'link': {
    ...                                 'type': 'item_list',
    ...                                 'href': '/v1/playable_list/2TzewA',
    ...                             },
    ...                         },
    ...                     },
    ...                 }
    ...             ]
    ...         }
    ...     ],
    ... }
    >>> tuple(crawl_for_key(data, 'primary_action'))
    ({'type': 'navigate', 'payload': {'link': {'type': 'feature', 'href': '/v1/playable_list/2TzewA'}}},)
    """
    # match type(data):
    #    case Mapping():
    if isinstance(data, Mapping):
        if value := data.get(key):
            yield value
        yield from itertools.chain.from_iterable(
            crawl_for_key(v, key) for k, v in data.items()
        )
    #   case Sequence():
    elif isinstance(data, Sequence) and not isinstance(data, str):
        yield from itertools.chain.from_iterable(crawl_for_key(i, key) for i in data)
    #    case _:
    #        pass


def setup_background_bulk_generator(
    app: sanic.Sanic,
    endpoint_path: str,
    output_path: Path,
    cache_period: datetime.timedelta,
    retry_period: datetime.timedelta,
    headers: dict[str, str],
) -> None:
    async def generate_bulk_cache(app):
        log.info(
            f'BULK_CACHE: started background task: {endpoint_path} -> {output_path}'
        )

        def get_age(path) -> datetime.timedelta:
            if not path.exists():
                return datetime.timedelta(weeks=52)
            return datetime.datetime.now() - datetime.datetime.fromtimestamp(
                path.stat().st_mtime
            )

        async def _generate_bulk_cache():
            response = None
            try:
                log.info(f'BROKEN: Attempt to {endpoint_path=} {headers=} fails because /bulk_data stream response never compleats')
                _, response = await app.asgi_client.get(endpoint_path, headers=headers)
            except Exception as ex:
                log.exception(ex)
            else:
                if response and response.status == 200:
                    log.info(f"BULK_CACHE: writing {output_path}")
                    with output_path.open('wb') as f:
                        f.write(gzip.compress(response.body))
                else:
                    log.error(
                        f"BULK_CACHE: Failed to call '{endpoint_path}' in background process"
                    )

        while True:
            if (cache_period - get_age(output_path)) < datetime.timedelta():
                log.info(
                    f'BULK_CACHE: {output_path=} older than {cache_period=} - regenerating bulk cache'
                )
                await _generate_bulk_cache()

            sleep_seconds = int(
                max(
                    retry_period.total_seconds(),
                    (cache_period - get_age(output_path)).total_seconds(),
                )
            )
            log.info(
                f'BULK_CACHE: sleeping for {sleep_seconds=} before next generation'
            )
            await asyncio.sleep(sleep_seconds)

    @app.main_process_start
    async def background_task(app):
        asyncio.create_task(generate_bulk_cache(app))
