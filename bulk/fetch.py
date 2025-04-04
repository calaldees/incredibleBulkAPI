import datetime
import logging
import typing as t
import urllib.request
from types import MappingProxyType
from pathlib import Path
import gzip
from dataclasses import dataclass
from functools import cached_property

import aiohttp
import ujson

from .cache_tools import DoNotPersistCacheException, cache_disk

log = logging.getLogger(__name__)


type Json = t.Mapping[str, Json | str | int | float | bool] | t.Sequence[Json | str | int | float | bool]
type FetchJsonCallable = t.Callable[[RequestParams], t.Awaitable[Json]]

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



class RequestParams(t.NamedTuple):
    """
    An immutable/hashable representation of all the parameters to make a URL request
    This NamedTuple can be used as a cache/hash key
    Pattern: Parameters are prepared independently before a fetch
    This pattern helps separate the data-fetching for request logic

    This automatically encodes json data for POSTs
    """
    url: str
    headers: frozenset[tuple[str, str]]
    method: str = 'GET'
    data: bytes = b''

    @classmethod
    def build(cls, url: str, headers: t.Mapping[str, str] = MappingProxyType({}), method='GET', data: bytes = b'', json: str | Json = '') -> t.Self:
        assert url
        assert not (bool(data) and bool(json)), 'only `data` or `json` can be provided'
        if json:
            #if isinstance(json, str):
            #    data = json
            #else:
            data = ujson.dumps(json).encode('utf8')
            headers = {"Content-Type": "application/json", **headers}
        return cls(url=url, headers=frozenset(headers.items()), method=method, data=data)

    def asdict(self) -> dict[str, t.Any]:
        return self._asdict() | {'headers': dict(self.headers)}


@dataclass(frozen=True)
class CachePath():
    path: Path = Path('_generated/cache')
    ttl: datetime.timedelta = datetime.timedelta(minutes=10)
    def __post_init__(self):
        self.path.mkdir(exist_ok=True)


@dataclass(frozen=True)
class CacheFile():
    params: RequestParams
    cache_path: CachePath

    @cached_property
    def path(self) -> Path:
        return self.cache_path.path.joinpath(str(hash(self.params))+'.json.gz')

    @property
    def expired(self) -> bool:
        return (
            not self.path.exists() or
            datetime.datetime.fromtimestamp(self.path.stat().st_mtime) < datetime.datetime.now() - self.cache_path.ttl
        )


async def fetch_json_cache(
    params: RequestParams,
    cache_path: CachePath,
) -> Json:
    """
    The cache files can be served by nginx as pre-compressed payloads
    """
    cache_file = CacheFile(params, cache_path)

    if not cache_file.expired:
        log.debug(f'loading from cache {params.url=}')
        # TODO: Async?
        with gzip.GzipFile(cache_file.path, mode='rb') as f:
            return ujson.load(f)

# from gzip_stream import GZIPCompressedStream
# with open('my_very_big_1tb_file.txt') as file_to_upload:
#     compressed_stream = GZIPCompressedStream(
#         file_to_upload,
#         compression_level=7
#     )
#     upload_client.upload_fileobj(compressed_stream)

    # TODO: async?
    with urllib.request.urlopen(urllib.request.Request(**params.asdict())) as response:
        response_body = response.read()
        response_status = response.status
        assert 'json' in response.headers.get('content-type', '')

    # TODO: async?
    if response_status == 200:
        with gzip.GzipFile(cache_file.path, mode='wb') as f:
            f.write(response_body)

    return ujson.loads(response_body)


#class Fetch(t.Protocol):
#    async def fetch_json(self, params: RequestParams) -> Json: ...

# t.Callable[[URLParams], t.Awaitable[APIPayload]]
# Explanation of t.Awaitable pattern https://stackoverflow.com/a/59177557/3356840