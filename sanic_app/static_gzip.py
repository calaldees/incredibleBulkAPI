import datetime
from pathlib import Path

import sanic


async def static_gzip(request: sanic.Request, path: Path) -> sanic.HTTPResponse:
    """
    curl --compressed --url http://localhost:8000/bulk/test.json.gz

    This endpoint exists as a helped to aid local development in python without dependencies
    In production bulk cache files are served directly from nginx
    """
    if "gzip" not in request.headers.get("Accept-Encoding", ""):
        raise sanic.exceptions.BadRequest("gzip encoding is required")
    path: Path = request.app.config.PATH_STATIC.joinpath(path)
    if not path.exists():
        # 307 - TEMPORARY REDIRECT - https://stackoverflow.com/a/12281287/3356840
        #return sanic.response.redirect(request.path, status=307, headers={"Retry-After": 360})
        raise sanic.exceptions.NotFound()
    age: datetime.timedelta = datetime.datetime.now() - datetime.datetime.fromtimestamp(path.stat().st_mtime)
    #cache_period = request.app.ctx.BULK_CACHE_REGEN_PERIOD
    return await sanic.response.file_stream(
        path,
        headers={
            #"Cache-Control": f"max-age={int((cache_period - age).total_seconds())}",  # TODO
            "Age": f"{int(age.total_seconds())}",
            "Content-Encoding": "gzip",
            "Content-Type": "application/json",
            "Content-Length": str(path.stat().st_size),
        },
    )
