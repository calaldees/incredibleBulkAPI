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


class AbstractSiteModel:
    name: str
    endpoint: str
    root_path: APIPath = "/"
    headers: t.Mapping[str, str] = {}
    fetch_json: FetchJsonCallable
    cache_period: datetime.timedelta

    async def crawl(self) -> APIBulk:
        cache: APIBulk = {}
        to_crawl: t.Mapping[APIPath, APIDepth] = {self.root_path: 0}
        while to_crawl:
            api_path, depth = to_crawl.popitem()
            log.info(
                f"to_crawl={len(to_crawl)} fetched={len(cache.keys())} {api_path=}"
            )
            # TODO: put this limiter behind an ENV var to allow people a lightweight demo?
            #if len(cache.keys()) > 5:  # TEMP! to test!!
            #    break
            payload = await self.get_api_path(api_path)
            cache[api_path] = payload
            if not self.continue_crawl(api_path, depth, payload):
                continue
            for path in islice(self.extract_crawl_paths(api_path, payload), 10):
                # TODO BUG: not quite right, we want to replace if depth is lower
                to_crawl.setdefault(path, depth + 1)
            for key in to_crawl.keys() & cache.keys():
                del to_crawl[key]
        return cache

    async def get_api_path(self, path: APIPath) -> APIPayload:
        """
        Perform the actual fetch of data
        """
        return await self.fetch_json(RequestParams.build(url=self.endpoint+path, headers=self.headers))

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
