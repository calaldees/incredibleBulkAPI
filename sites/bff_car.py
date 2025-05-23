import datetime
import re
import typing as t

from bulk.data import crawl_for_key, get_path
from bulk.site_model import AbstractSiteModel, APIBulk, APIDepth, APIPath, APIPayload, FetchJsonCallable
from bulk.image_model import AbstractImageModel, ImageUrl, FetchImageBase64Callable


class BffCarSiteModel(AbstractSiteModel):
    name = 'bff-car'
    cache_period = datetime.timedelta(hours=1, minutes=1)

    def __init__(self, fetch_json: FetchJsonCallable, endpoint: str = 'https://bff-car-guacamole.musicradio.com'):
        self.fetch_json = fetch_json
        self.endpoint = endpoint
        self.headers = {"Accept": "application/vnd.global.6+json"}
        self.root_path: APIPath = '/features'

    @t.override
    def extract_crawl_paths(self, path: APIPath, payload: APIPayload) -> t.Iterable[APIPath]:
        """
        >>> from functools import partial
        >>> extract_crawl_paths = partial(BffCarSiteModel.extract_crawl_paths, None)
        >>> extract_crawl_paths(None, {})
        set()
        >>> extract_crawl_paths(
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
        if get_path(payload, "0.slug"):  # v5 responses with slug
            return {f"{path}/{i.get('slug')}" for i in payload}
        if get_path(payload, "0.path"):  # v6 responses with path
            return {i.get('path') for i in payload}
        # CarPage - crawl for primary_action navigate hrefs
        #car_page_navigate_hrefs: set[str] = set(
        return \
            filter(None, (
                get_path(primary_action, "payload.link.href")  # type: ignore
                for primary_action in crawl_for_key(payload, "primary_action")
            ))
        #)
        # set(
        # TODO: cache Playables
        # get_path(primary_action, 'payload.id')
        # Although these are calls to `bff-mobile` and may need more client work
        # )
        #return car_page_navigate_hrefs


    @t.override
    def continue_crawl(self, path: APIPath, depth: APIDepth, payload: APIPayload) -> bool:
        if path.startswith("/catchup/brand_group/"):
            return False
        #if path.startswith("/features/"):
        #    return False
        if "playable_list" in path: # and depth > 1:
            # v6 now has podcasts on the main page - so we have LOADS of podcast episodes. Investigate
            #
            # `playable_lists`` are all postcasts and episodes - catchup is on a different url -
            # 'playable_list' in url and depth > 2 == gives 582 pages uncompressed6.4mb  gzip0.84mb
            # no depth full 1300 pages uncompressed 32mb gzip 4.2mb
            # depth > 2 - gives 175 uncompressed 5.4mb gzip 0.75mb
            return False
        return True


class BffCarImageModel(AbstractImageModel):
    name = 'bff-car-images'

    SKIP_URL_REGEX = (
        #re.compile("/features/.*"),
        #re.compile("/catchup/.*"),
        re.compile(".*/lists/.*"),
        re.compile(".*/playable_list/.*"),
    )

    def __init__(self, fetch_image_preview_base64: FetchImageBase64Callable):
        self.fetch_image_preview_base64 = fetch_image_preview_base64

    @t.override
    def extract_image_urls(self, data: APIBulk) -> t.Iterable[ImageUrl]:
        for api_path, api_payload in data.items():
            if any(regex.match(api_path) for regex in self.SKIP_URL_REGEX):
                continue
            yield from (
                image_url
                for image_url in crawl_for_key(api_payload, "url")
                if any(i in image_url for i in ('global', 'musicrad', 'bff-car'))
            )
