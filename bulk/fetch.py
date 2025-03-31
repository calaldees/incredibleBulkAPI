import datetime
import http.client
import logging
import typing as t
import urllib.request
from types import MappingProxyType
from pathlib import Path
import pickle
import zlib
import gzip

import aiohttp
import ujson

from .cache_tools import DoNotPersistCacheException, cache_disk

log = logging.getLogger(__name__)


type Json = t.Mapping[str, Json | str | int | float | bool] | t.Sequence[Json | str | int | float | bool]


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




class URLParams(t.NamedTuple):
    url: str
    headers: t.Mapping[str, str]
    method: str = 'GET'
    data: str | bytes = b''

    @classmethod
    def build(cls, url='', headers=MappingProxyType({}), method='GET', data: str | bytes = b'', json: str | Json = ''):
        assert url
        assert bool(data) ^ bool(json)
        if json:
            if isinstance(json, str):
                data = json
            else:
                data = ujson.dumps(json)
                headers = {"Content-Type": "application/json"} | headers
        return cls(
            url=url,
            headers=headers,
            method=method,
            data = data,
        )

    @property
    def hash(self, *args, **kwargs) -> str:
        return str(zlib.adler32(pickle.dumps(self)))


async def fetch_json_cache(
    params: URLParams,
    cache_path: Path = Path('_generated/cache'),
    ttl: datetime.timedelta = datetime.timedelta(minutes=10),
) -> Json:
    """
    The cache files can be served by nginx as pre-compressed payloads
    """
    cache_path = cache_path.joinpath(params.hash+'.json.gz')

    if cache_path.is_file() and (
        datetime.datetime.fromtimestamp(cache_path.stat().st_mtime) > datetime.datetime.now() - ttl
    ):
        log.debug(f'loading from cache {params.url=}')
        # TODO: Async?
        with gzip.GzipFile(cache_path, mode='rb') as f:
            return ujson.load(f)

    # TODO: async?
    with urllib.request.urlopen(urllib.request.Request(**params._asdict())) as response:
        response_body = response.read()
        response_status = response.status
        assert 'json' in response.headers.get('content-type', '')

    # TODO: async?
    if response_status == 200:
        with gzip.GzipFile(cache_path, mode='wb') as f:
            f.write(response_body)

    return ujson.loads(response_body)
