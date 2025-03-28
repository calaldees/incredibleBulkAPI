import asyncio
import datetime
import logging
from pathlib import Path

import sanic
from sanic.log import logger as log

from .static_gzip import static_gzip

logging.basicConfig(level=logging.DEBUG)

app = sanic.Sanic("incredibleBulkAPI")

# Static Gzip
# app.ext.add_dependency(Path, lambda **kwargs: Path(kwargs['path']))
app.config.PATH_STATIC = Path("_generated")
if not app.config.PATH_STATIC.is_dir():
    raise Exception(f"{app.config.PATH_STATIC=} must exist")
app.add_route(static_gzip, "/_generated/<path:str>")

# Root README
app.config.README = Path("README.md").read_text()


@app.route("/")
async def root(request):
    return sanic.response.text(app.config.README)


# app.config.BULK = json.loads(Path("bulk.config.json").read_text())

# Future: Dynamically import .sites handlers using `importlib`
# For now - we can import directly
from sites.bff_car import BffCarSiteModel

from .background_fetch import create_background_bulk_crawler_coroutine


@app.main_process_start
async def background_task(app):
    asyncio.create_task(
        create_background_bulk_crawler_coroutine(
            site_model=BffCarSiteModel(),
            path_destination=app.config.PATH_STATIC.joinpath("bff-car.json.gz"),
            cache_period=datetime.timedelta(minutes=2),  # hours=1
            retry_period=datetime.timedelta(seconds=10),
        ),
    )
