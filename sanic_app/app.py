import datetime
import logging
from pathlib import Path
from functools import partial

import sanic
#from sanic.log import logger as log


logging.basicConfig(level=logging.DEBUG)

app = sanic.Sanic("incredibleBulkAPI")

app.config.README = Path("README.md").read_text()
@app.route("/")
async def root(request) -> sanic.HTTPResponse:
    return sanic.response.text(app.config.README)


# Static Gzip serving for local only - in production this is handled by nginx
# app.ext.add_dependency(Path, lambda **kwargs: Path(kwargs['path']))
from .static_gzip import static_gzip
app.config.PATH_STATIC = Path("_generated")
if not app.config.PATH_STATIC.is_dir():
    raise Exception(f"{app.config.PATH_STATIC=} must exist")
app.add_route(static_gzip, "/_generated/<path:str>")
# curl --compressed --url http://localhost:8000/_generated/test.json.gz


from bulk.fetch import RequestParams, CachePath, CacheFile
cache_path = cache_path=CachePath(
    path=app.config.PATH_STATIC.joinpath('cache'),
    ttl=datetime.timedelta(minutes=5),
)
@app.route("/fetch")
async def redirect_to_cache_file(request: sanic.Request) -> sanic.HTTPResponse:
    # TODO:
    breakpoint()
    #RequestParams()
    request.args
    request.form
    request.json
    #sanic.response.
    return sanic.response.json({})
    #    params normalised from query_string and body (form or json encoded) as ParamSpecKwargs?
    #     return sanic.response.raw(body=await fetch_url(url, method, headers, data), status=200, content_type='application/json', headers={"Age": f"{int(age.total_seconds())}"})

from bulk.fetch import FetchJsonCallable, fetch_json_cache
fetch: FetchJsonCallable = partial(
    fetch_json_cache,
    cache_path=cache_path,
)
from bulk.background_fetch import create_background_bulk_crawler_task
from sites.bff_car import BffCarImageModel, BffCarSiteModel
# Future: Dynamically import .sites handlers using `importlib`
# For now - we can import directly
# the output gzip filenames can be inferred from the class name of the SiteModel
# will have to think about the cache_period
app.add_task(
    create_background_bulk_crawler_task(
        site_model=BffCarSiteModel(fetch),
        image_model=BffCarImageModel(),
        path_gzip_data=app.config.PATH_STATIC.joinpath("bff-car.json.gz"),
        path_gzip_images=app.config.PATH_STATIC.joinpath("bff-car-images.json.gz"),
        cache_period=datetime.timedelta(minutes=2),  # hours=1
        retry_period=datetime.timedelta(seconds=10),
    )
)