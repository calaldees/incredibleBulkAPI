import datetime
import re
import typing as t

from bulk.data import crawl_for_key, get_path
from bulk.site_model import AbstractSiteModel, APIBulk, APIDepth, APIPath, APIPayload, FetchCallable


class BffMobileArticleModel(AbstractSiteModel):
    name = 'bff-mobile'
    cache_period = datetime.timedelta(hours=1, minutes=1)  # TODO: consider that this is doing for different platforms

    def __init__(self, fetch: FetchCallable, endpoint: str = 'https://bff-mobile-guacamole.musicradio.com'):
        self.fetch = fetch
        self.endpoint = endpoint
        self.headers = {"accept": "application/vnd.global.22+json"}
        self.root_path: APIPath = '/features/news/all-users'

    @t.override
    def extract_crawl_paths(self, path: APIPath, payload: APIPayload) -> t.Iterable[APIPath]:

        #title = payload['title']

        article_hrefs = tuple(
            link['href']
            for link in crawl_for_key(payload, "link")
            if link.get('type') == 'article'
        )
        return article_hrefs

        #)
        # set(
        # TODO: cache Playables
        # get_path(primary_action, 'payload.id')
        # Although these are calls to `bff-mobile` and may need more client work
        # )
        #return car_page_navigate_hrefs


    @t.override
    def continue_crawl(self, path: APIPath, depth: APIDepth, payload: APIPayload) -> bool:
        return True
