import typing as t
import asyncio
import datetime
import gzip
import logging
from pathlib import Path

import ujson

from bulk.site_model import AbstractSiteModel

log = logging.getLogger(__name__)


def create_background_bulk_crawler_coroutine(
    site_model: AbstractSiteModel,
    path_destination: Path,
    cache_period: datetime.timedelta,
    retry_period: datetime.timedelta,
) -> t.Coroutine[t.Any, t.Any, t.NoReturn]:

    async def generate_bulk_cache():
        log.info(
            f"BULK_CACHE: started background task: {site_model=} -> {path_destination=}"
        )

        def get_age(path: Path) -> datetime.timedelta:
            if not path.exists():
                return datetime.timedelta(weeks=52)
            return datetime.datetime.now() - datetime.datetime.fromtimestamp(path.stat().st_mtime)

        async def _generate_bulk_cache():
            try:
                cache = await site_model.crawl()
            except Exception as ex:
                log.exception(ex)
            else:
                log.info(f"BULK_CACHE: writing {path_destination}")
                with gzip.open(path_destination, 'wt', encoding='UTF-8') as zipfile:
                    ujson.dump(cache, zipfile)

        while True:
            if (cache_period - get_age(path_destination)) < datetime.timedelta():
                log.info(
                    f"BULK_CACHE: {path_destination=} older than {cache_period=} - regenerating bulk cache"
                )
                await _generate_bulk_cache()

            sleep_seconds = int(
                max(
                    retry_period.total_seconds(),
                    (cache_period - get_age(path_destination)).total_seconds(),
                )
            )
            log.info(
                f"BULK_CACHE: sleeping for {sleep_seconds=} before next generation"
            )
            await asyncio.sleep(sleep_seconds)

    return generate_bulk_cache()
