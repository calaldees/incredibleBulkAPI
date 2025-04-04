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

app.static('/static/', Path('static/'))


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
cache_path_data = CachePath(path=app.config.PATH_STATIC.joinpath('cache'))
@app.route("/fetch")
async def redirect_to_cache_file(request: sanic.Request) -> sanic.HTTPResponse:
    params: dict[str, str] = {**dict(request.query_args), **request.form, **(request.json or {})}
    url = params.pop('url', '')
    if not url:
        raise sanic.exceptions.BadRequest('url missing')
    # resolve the `cache_file` in the same way that `fetch_json_cache` builds filenames
    cache_file = CacheFile(
        params=RequestParams.build(url, method=params.pop('method', 'GET'), headers=params),
        cache_path=cache_path_data,
        file_suffix='.json.gz',
    )
    path = str(cache_file.path.relative_to(app.config.PATH_STATIC)).removesuffix('.gz')
    return sanic.response.convenience.redirect(to=app.url_for('static_json_gzip', path=path))



from bulk.fetch import FetchJsonCallable, FetchImageBase64Callable, fetch_json_cache, fetch_image_preview_cache
from bulk.background_fetch import create_background_bulk_crawler_task
from sites.bff_car import BffCarImageModel, BffCarSiteModel
# Future: Dynamically import .sites handlers using `importlib`
# For now - we can import directly
fetch_json: FetchJsonCallable = partial(
    fetch_json_cache,
    cache_path=CachePath(path=cache_path_data.path, ttl=BffCarSiteModel.cache_period)
)
fetch_image_preview: FetchImageBase64Callable = partial(
    fetch_image_preview_cache,
    cache_path=CachePath(path=app.config.PATH_STATIC.joinpath('images'), ttl=datetime.timedelta(weeks=52)),
    image_preview_service_endpoint="http://image_preview_api:8000",
)
app.add_task(
    create_background_bulk_crawler_task(
        site_model=BffCarSiteModel(fetch_json),
        image_model=BffCarImageModel(fetch_image_preview),
        path=app.config.PATH_STATIC,
    )
)