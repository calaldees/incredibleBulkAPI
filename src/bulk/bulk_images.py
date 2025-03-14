import datetime
import re
from pathlib import Path
from typing import Iterator, TypeAlias

import httpx
import sanic
from sanic.log import logger as log

from . import crawl_for_key, setup_background_bulk_generator
from .cache_tools import DoNotPersistCacheException, cache_disk

IMAGE_PREVIEW_SERVICE = 'http://host.docker.internal:8000'


@cache_disk(ttl=datetime.timedelta(weeks=52))
async def get_image_preview_avif_base64(url) -> str:
    log.info(f'fetch image preview for {url[-8:]}')
    response = None
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                IMAGE_PREVIEW_SERVICE,
                json={'url': url},
            )
        if response and response.status_code == 200:
            return response.text
    except Exception as e:
        log.exception(e)
    raise DoNotPersistCacheException()


def progress(ii):
    count = 0
    for i in ii:
        count += 1
        if count % 100 == 0:
            print(count)
        yield i


Url: TypeAlias = str
CarResponse: TypeAlias = dict
ImageUrl: TypeAlias = Url


def select_subset_of_image_url_from_bulk_data(
    bulk_data: dict[Url, CarResponse],
) -> Iterator[ImageUrl]:
    ALLOWED_URL_REGEX = (
        re.compile('/features/.*'),
        re.compile('/catchup/.*'),
    )
    for url, car_response in bulk_data.items():
        if any(regex.match(url) for regex in ALLOWED_URL_REGEX):
            yield from (
                image_url
                for image_url in crawl_for_key(car_response, 'url')
                if 'images.' in image_url
            )


async def _bulk_images(request: sanic.Request) -> sanic.HTTPResponse:
    """
    curl --compressed --header "Accept: application/vnd.global.5+json" --url http://localhost:9100/_bulk_images > ~/Downloads/bulk_images.json
    """
    request, response = await request.app.asgi_client.get(
        '/bulk_data', headers=request.headers
    )
    return sanic.response.json({
        url: await get_image_preview_avif_base64(url)
        for url in select_subset_of_image_url_from_bulk_data(response.json)
    })


async def bulk_images(request: sanic.Request) -> sanic.HTTPResponse:
    """
    curl --compressed --header "Accept: application/vnd.global.5+json" --url http://localhost:9100/bulk_images > ~/Downloads/bulk_images.json
    """
    if 'gzip' not in request.headers.get('Accept-Encoding', ''):
        raise sanic.exceptions.BadRequest('gzip encoding is required')
    cache_period = request.app.ctx.BULK_CACHE_REGEN_PERIOD
    path = request.app.ctx.BULK_CACHE_OUTPUT_PATH_IMAGES
    if not path.exists():
        # 307 - TEMPORARY REDIRECT - https://stackoverflow.com/a/12281287/3356840
        return sanic.response.redirect(
            request.path, status=307, headers={'Retry-After': 360}
        )
    age: datetime.timedelta = datetime.datetime.now() - datetime.datetime.fromtimestamp(
        path.stat().st_mtime
    )
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


def register_bulk_image_generator(app: sanic.Sanic):
    app.ctx.BULK_CACHE_OUTPUT_PATH_IMAGES = Path('cache_bulk_images.json.gz')

    app.add_route(_bulk_images, '/_bulk_images')
    app.add_route(bulk_images, '/bulk_images')

    setup_background_bulk_generator(
        app,
        endpoint_path='/_bulk_images',
        output_path=app.ctx.BULK_CACHE_OUTPUT_PATH_IMAGES,
        cache_period=app.ctx.BULK_CACHE_REGEN_PERIOD,
        retry_period=app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD,
        headers={'Accept': 'application/vnd.global.5+json'},
    )
