from __future__ import annotations

import datetime
import logging
import typing as t
from itertools import islice
from abc import abstractmethod

from .fetch import RequestParams

log = logging.getLogger(__name__)


type APIPath = str
type APIDepth = int
type APIPayload = t.Mapping[str, t.Any] | t.Sequence[t.Any]
type APIBulk = t.Mapping[APIPath, APIPayload]
type FetchJsonCallable = t.Callable[[RequestParams], t.Awaitable[APIPayload]]

type Payload = str | APIPayload
type FetchCallable = t.Callable[[RequestParams], t.Awaitable[Payload]]


class AbstractSiteModel:
    name: str
    endpoint: str
    root_path: APIPath = "/"
    headers: t.Mapping[str, str] = {}
    fetch: FetchCallable  # This is typed incorrectly, what if we want to get other types .. Oh no
    cache_period: datetime.timedelta

    async def crawl(self) -> APIBulk:
        bulk: APIBulk = {}
        to_crawl: t.Mapping[APIPath, APIDepth] = {self.root_path: 0}
        while to_crawl:
            path, depth = to_crawl.popitem()
            log.info(
                f"to_crawl={len(to_crawl)} fetched={len(bulk.keys())} {path=}"
            )
            # TODO: put this limiter behind an ENV var to allow people a lightweight demo?
            #if len(cache.keys()) > 5:  # TEMP! to test!!
            #    break
            if path.startswith('/'):
                payload = await self.get_api_path(path)
            else:
                payload = await self.fetch(RequestParams.build(url=path, headers={'accept': 'text/html'}))
            bulk[path] = payload
            if isinstance(payload, str):  # INCORRECT! HACK
                continue
            if not self.continue_crawl(path, depth, payload):
                continue
            for path in self.extract_crawl_paths(path, payload): #  islice(, 10):
                # TODO BUG: not quite right, we want to replace if depth is lower
                to_crawl.setdefault(path, depth + 1)
            for key in to_crawl.keys() & bulk.keys():
                del to_crawl[key]
        return bulk

    async def get_api_path(self, path: APIPath) -> APIPayload:
        """
        Perform the actual fetch of data
        """
        return await self.fetch(RequestParams.build(url=self.endpoint+path, headers=self.headers))

    @abstractmethod
    def continue_crawl(
        self, path: APIPath, depth: APIDepth, payload: APIPayload
    ) -> bool:
        """
        The current item has been added to the cache - do we proceed with more crawling?
        """
        ...

    @abstractmethod
    def extract_crawl_paths(
        self, path: APIPath, payload: APIPayload
    ) -> t.Iterable[APIPath]:
        """
        Identify all sub-pages/paths to crawl next
        """
        ...
