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


def create_background_bulk_crawler_task(
    site_model: AbstractSiteModel,
    image_model: AbstractImageModel,
    path_gzip_data: Path,
    path_gzip_images: Path,
    cache_period: datetime.timedelta,
    retry_period: datetime.timedelta,
) -> t.Callable[..., t.Awaitable[t.NoReturn]]:

    semaphore = asyncio.Semaphore(1)

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
                return
            else:
                # TODO: Async write?
                log.info(f"BULK_CACHE: writing {path_gzip_data}")
                with gzip.open(path_gzip_data, 'wt', encoding='UTF-8') as zipfile:
                    ujson.dump(api_bulk, zipfile)

            # Generate Image Previews
            try:
                api_bulk_images = await image_model.image_previews(api_bulk)
            except Exception as ex:
                log.exception(ex)
            else:
                # TODO: Async write?
                log.info(f"BULK_CACHE: writing {path_gzip_images}")
                with gzip.open(path_gzip_images, 'wt', encoding='UTF-8') as zipfile:
                    ujson.dump(api_bulk_images, zipfile)


        while True:
            # Semaphore gate
            # This process is spawned each time a worker thread/task is created
            # Only allow one async task to proceed with `_generate_bulk_cache` at a time
            # Bug: Sadly, when _generate_bulk_cache fails, and does not update the file, all the workers try in sequence again before sleeping
            async with semaphore:
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

    return None
    return generate_bulk_cache
