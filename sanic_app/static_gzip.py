import datetime
from pathlib import Path

import sanic


async def static_json_gzip(request: sanic.Request, path: Path) -> sanic.HTTPResponse:
    """
    In production bulk cache files are served directly from nginx
    This endpoint exists as a helped to aid local development in python without dependencies
    """
    if "gzip" not in request.headers.get("Accept-Encoding", ""):
        raise sanic.exceptions.BadRequest("gzip encoding is required")
    path: Path = request.app.config.PATH_STATIC.joinpath(path)
    if path.suffix != '.json':
        raise sanic.exceptions.BadRequest("only json files can be served")
    path = path.parent.joinpath(path.name + '.gz')
    if not path.exists():
        # 307 - TEMPORARY REDIRECT - https://stackoverflow.com/a/12281287/3356840
        # Firefox does not seem to understand the 'Retry-After'
        #return sanic.response.redirect(request.path, status=307, headers={"Retry-After": 360})
        raise sanic.exceptions.NotFound()
    age: datetime.timedelta = datetime.datetime.now() - datetime.datetime.fromtimestamp(path.stat().st_mtime)
    #cache_period = request.app.ctx.BULK_CACHE_REGEN_PERIOD
    headers = {
        #"Cache-Control": f"max-age={int((cache_period - age).total_seconds())}",  # TODO
        "Age": f"{int(age.total_seconds())}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
        "Content-Length": str(path.stat().st_size),
        "Access-Control-Allow-Origin": "*",
    }
    if request.method == 'GET':
        return await sanic.response.file_stream(path, headers=headers)
    if request.method == 'HEAD':
        return sanic.response.HTTPResponse(headers=headers)
    raise sanic.exceptions.MethodNotSupported()
