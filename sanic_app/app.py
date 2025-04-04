import datetime
import logging
from pathlib import Path
from functools import partial

import sanic
#from sanic.log import logger as log


logging.basicConfig(level=logging.DEBUG)

app = sanic.Sanic("incredibleBulkAPI")
app.config.FALLBACK_ERROR_FORMAT = 'json'


app.config.README = Path("README.md").read_text()
@app.route("/")
async def root(request) -> sanic.HTTPResponse:
    return sanic.response.text(app.config.README)
@app.route("/favicon.ico")
async def favicon(request) -> sanic.HTTPResponse:
    return sanic.response.convenience.empty()  # suppress browser exception spam


# Static Gzip serving for local only - in production this is handled by nginx
# app.ext.add_dependency(Path, lambda **kwargs: Path(kwargs['path']))
app.config.PATH_STATIC = Path("./static_json_gzip/")
if not app.config.PATH_STATIC.is_dir():
    raise Exception(f"{app.config.PATH_STATIC=} must exist")
from .static_gzip import static_json_gzip
app.add_route(static_json_gzip, "/static_json_gzip/<path:path>")
# curl --compressed --url http://localhost:8000/static_json_gzip/bff-car.json (should be encoded gzip)
# curl --compressed --url http://localhost:8000/static_json_gzip/cache/-28682793412047709.json


from bulk.fetch import RequestParams, CachePath, CacheFile
cache_path = CachePath(
    path=app.config.PATH_STATIC.joinpath('cache'),
    ttl=datetime.timedelta(minutes=5),
)
@app.route("/fetch")
async def redirect_to_cache_file(request: sanic.Request) -> sanic.HTTPResponse:
    params: dict[str, str] = {**dict(request.query_args), **request.form, **(request.json or {})}
    url = params.pop('url', '')
    if not url:
        raise sanic.exceptions.BadRequest('url missing')
    cache_file = CacheFile(
        params=RequestParams.build(url, method=params.pop('method', 'GET'), headers=params),
        cache_path=cache_path,
    )
    return sanic.response.convenience.redirect(
        to=app.url_for('static_json_gzip', path=cache_file.file.removesuffix('.gz'))
    )


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