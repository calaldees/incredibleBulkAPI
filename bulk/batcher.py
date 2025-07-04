# Spinoff project to batch websites
import asyncio
from pprint import pprint as pp
from functools import partial
from collections.abc import Mapping, Sequence
import logging
from pathlib import Path
import json

import aiohttp

from .data import crawl_for_key
from .fetch2 import RequestParams, Response
from .url import compose_url

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


type JsonPrimitives = str | int | float | bool | None
type Json = Mapping[str, Json | JsonPrimitives] | Sequence[Json | JsonPrimitives]
type JsonObject = Mapping[str, Json | JsonPrimitives]


async def get(session: aiohttp.ClientSession, params: RequestParams) -> Response:
    log.info(params.url)
    async with session.request(**params.asdict(), ssl=False) as response:
        return Response(
            request=params,
            status=response.status,
            headers=response.headers,
            data=await response.read(),
        )
        # assert 'text' in response.content_type
        # response_status = response.status
        # if "json" in response.content_type:
        #    response_data = await response.json()
    # breakpoint()


async def main():
    http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))
    _get = partial(
        get, http_session
    )
    async def _image_preview(url):
        return (await _get(RequestParams.build(url=compose_url('http://image_preview_api:8000/', query=dict(url=url))))).text

    #article_hrefs = ('https://articles.globalplayer.com/7giH6CgVXGUeDGr6BzL4fK6Eni',)

    bulk: Json = {}

    news_json = (
        await _get(
            RequestParams.build(
                url=compose_url(
                    urlstring="https://bff-mobile-guacamole.musicradio.com",
                    path="/features/news/all-users",
                ),
                headers={"accept": "application/vnd.global.22+json"},
            ),
        )
    ).json

    bulk['/features/news/all-users'] = news_json

    article_hrefs = tuple(
        link["href"]
        for link in crawl_for_key(news_json, "link")
        if link.get("type") == "article"
    )[:4]

    for article_href in article_hrefs:
        html = (await _get(RequestParams.build(url=article_href))).html
        css = tuple(link['href'] for link in html.find_all('link', rel='stylesheet'))
        imgs = {
            img_url: await _image_preview(img_url)
            for img_url in tuple(img['src'] for img in html.find_all('img'))
        }
        bulk |= {
            article_href: str(html),
            **imgs,
        }

    with Path('/app/static_json_gzip/bulk_articles.json').open('w') as fp:
        json.dump(bulk, fp)

    await http_session.close()

    return bulk

if __name__ == "__main__":
    asyncio.run(main())
