import dataclasses
import datetime
import gzip
import logging
import pickle
import typing as t
import urllib.request
from functools import cached_property
from pathlib import Path
from types import MappingProxyType
from zlib import adler32

import aiohttp
import ujson

log = logging.getLogger(__name__)


type Json = t.Mapping[str, Json | str | int | float | bool] | t.Sequence[Json | str | int | float | bool]
type FetchJsonCallable = t.Callable[[RequestParams], t.Awaitable[Json]]

type ImageUrl = str
type Base64EncodedImage = str
type FetchImageBase64Callable = t.Callable[[ImageUrl], t.Awaitable[Base64EncodedImage]]



@dataclasses.dataclass(frozen=True)
class RequestParams():
    """
    An immutable/hashable representation of all the parameters to make a URL request
    This NamedTuple can be used as a cache/hash key
    Pattern: Parameters are prepared independently before a fetch
    This pattern helps separate the data-fetching for request logic

    This automatically encodes json data for POSTs

    consider being compatible with other request types
    httpx - https://www.python-httpx.org/api/#request
        method, url, [params], [headers], [cookies], [content], [data], [files], [json], [stream]
    urllib - https://docs.python.org/3/library/urllib.request.html#urllib.request.Request
        url, data=None, headers={}, origin_req_host=None, unverifiable=False, method=None
    requests - https://requests.readthedocs.io/en/latest/api/#requests.request
        method, url [params], data, json, headers, cookies, files, auth, timeout, allow_redirects, stream
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
        return dataclasses.asdict(self) | {'headers': dict(self.headers)}

    def __hash__(self) -> int:
        return adler32(pickle.dumps(dataclasses.astuple(self)))  # stable data hash


@dataclasses.dataclass(frozen=True)
class CachePath():
    path: Path = Path('static_json_gzip/cache')
    ttl: datetime.timedelta = datetime.timedelta(minutes=10)
    def __post_init__(self):
        self.path.mkdir(exist_ok=True)


@dataclasses.dataclass(frozen=True)
class CacheFile():
    params: RequestParams
    cache_path: CachePath
    file_suffix: str = '.raw'

    @cached_property
    def file(self) -> str:
        return str(hash(self.params))+self.file_suffix

    @cached_property
    def path(self) -> Path:
        return self.cache_path.path.joinpath(self.file)

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
    cache_file = CacheFile(params, cache_path, file_suffix='.json.gz')

    if not cache_file.expired:
        log.debug(f'loading from cache {params.url=}')
        # TODO: async gzip-stream
        with gzip.GzipFile(cache_file.path, mode='rb') as f:
            return ujson.load(f)

    # Old sync request
    # with urllib.request.urlopen(urllib.request.Request(**params.asdict())) as response:
    #     response_body = response.read()
    #     response_status = response.status
    #     assert 'json' in response.headers.get('content-type', '')

    async with aiohttp.ClientSession() as session:
        async with session.request(**params.asdict(), timeout=5, ssl=False) as response:
            # assert 'json' in response.content_type
            response_status = response.status
            response_body = await response.read()

    # TODO: async gzip-stream
    if response_status == 200:
        with gzip.GzipFile(cache_file.path, mode='wb') as f:
            f.write(response_body)

    return ujson.loads(response_body)



async def fetch_image_preview_cache(
    image_url: ImageUrl,
    cache_path: CachePath,
    image_preview_service_endpoint: str
) -> Base64EncodedImage:
    params = RequestParams.build(
        method="POST",
        url=image_preview_service_endpoint,
        json={"url": image_url},
    )
    cache_file = CacheFile(params, cache_path, file_suffix='.txt')

    if not cache_file.expired:
        log.debug(f'loading from cache {image_url=}')
        return cache_file.path.read_text()

    log.info(f"fetch image preview for {image_url[-8:]}")
    # with urllib.request.urlopen(urllib.request.Request(**params.asdict())) as response:
    #     response_body = response.read()
    #     response_status = response.status
    #     assert 'text' in response.headers.get('content-type', '')
    async with aiohttp.ClientSession() as session:
        async with session.request(**params.asdict(), timeout=5, ssl=False) as response:
            # assert 'text' in response.content_type
            response_status = response.status
            response_body = await response.read()

    if response_status == 200:
        cache_file.path.write_bytes(response_body)

    return response_body.decode('utf8')
