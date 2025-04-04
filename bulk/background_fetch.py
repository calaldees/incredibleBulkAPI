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
    path: Path,
    retry_period: datetime.timedelta = datetime.timedelta(minutes=1),
) -> t.Callable[..., t.Awaitable[t.NoReturn]]:

    path_gzip_data = path.joinpath(site_model.name+'.json.gz')
    path_gzip_images = path.joinpath(image_model.name+'.json.gz')
    semaphore = asyncio.Semaphore(1)

    async def generate_bulk_cache():
        log.info(
            f"BULK_CACHE: started background task: {site_model=} -> {path_gzip_data=}"
        )

        def get_age(path: Path) -> datetime.timedelta:
            if not path.exists():
                return datetime.timedelta(weeks=52)
            return datetime.datetime.now() - datetime.datetime.fromtimestamp(path.stat().st_mtime)

        def rotate_output_file(file: Path):
            if file.exists():
                date_string = datetime.datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d-%H-%M')
                file.rename(path.joinpath(f'{file.name.removesuffix(".json.gz")}-{date_string}.json.gz'))

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
                rotate_output_file(path_gzip_data)
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
                rotate_output_file(path_gzip_images)
                with gzip.open(path_gzip_images, 'wt', encoding='UTF-8') as zipfile:
                    ujson.dump(api_bulk_images, zipfile)


        while True:
            # Semaphore gate
            # This process is spawned each time a worker thread/task is created
            # Only allow one async task to proceed with `_generate_bulk_cache` at a time
            # Bug: Sadly, when _generate_bulk_cache fails, and does not update the file, all the workers try in sequence again before sleeping
            async with semaphore:
                if (site_model.cache_period - get_age(path_gzip_data)) < datetime.timedelta():
                    log.info(
                        f"BULK_CACHE: {path_gzip_data=} older than {site_model.cache_period=} - regenerating bulk cache"
                    )
                    await _generate_bulk_cache()

            sleep_seconds = int(
                max(
                    retry_period.total_seconds(),
                    (site_model.cache_period - get_age(path_gzip_data)).total_seconds(),
                )
            )
            log.info(
                f"BULK_CACHE: sleeping for {sleep_seconds=} before next generation"
            )
            await asyncio.sleep(sleep_seconds)

    return generate_bulk_cache
