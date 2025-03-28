import asyncio
import datetime
import gzip
import logging
import typing as t
from pathlib import Path

import ujson

from bulk.image_model import AbstractImageModel
from bulk.site_model import AbstractSiteModel

log = logging.getLogger(__name__)


def create_background_bulk_crawler_coroutine(
    site_model: AbstractSiteModel,
    image_model: AbstractImageModel,
    path_gzip_data: Path,
    path_gzip_images: Path,
    cache_period: datetime.timedelta,
    retry_period: datetime.timedelta,
) -> t.Coroutine[t.Any, t.Any, t.NoReturn]:

    async def generate_bulk_cache():
        log.info(
            f"BULK_CACHE: started background task: {site_model=} -> {path_gzip_data=}"
        )

        def get_age(path: Path) -> datetime.timedelta:
            if not path.exists():
                return datetime.timedelta(weeks=52)
            return datetime.datetime.now() - datetime.datetime.fromtimestamp(path.stat().st_mtime)

        async def _generate_bulk_cache():
            # Generate Data
            try:
                api_bulk = await site_model.crawl()
            except Exception as ex:
                log.exception(ex)
            else:
                log.info(f"BULK_CACHE: writing {path_gzip_data}")
                with gzip.open(path_gzip_data, 'wt', encoding='UTF-8') as zipfile:
                    ujson.dump(api_bulk, zipfile)

            # Generate Image Previews
            try:
                api_bulk_images = await image_model.image_previews(api_bulk)
            except Exception as ex:
                log.exception(ex)
            else:
                log.info(f"BULK_CACHE: writing {path_gzip_images}")
                with gzip.open(path_gzip_images, 'wt', encoding='UTF-8') as zipfile:
                    ujson.dump(api_bulk_images, zipfile)


        while True:
            if (cache_period - get_age(path_gzip_data)) < datetime.timedelta():
                log.info(
                    f"BULK_CACHE: {path_gzip_data=} older than {cache_period=} - regenerating bulk cache"
                )
                await _generate_bulk_cache()

            sleep_seconds = int(
                max(
                    retry_period.total_seconds(),
                    (cache_period - get_age(path_gzip_data)).total_seconds(),
                )
            )
            log.info(
                f"BULK_CACHE: sleeping for {sleep_seconds=} before next generation"
            )
            await asyncio.sleep(sleep_seconds)

    return generate_bulk_cache()
