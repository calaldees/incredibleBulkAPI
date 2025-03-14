import json
from pathlib import Path

import sanic
from sanic.log import logger as log

from .static_gzip import static_gzip

app = sanic.Sanic("bulkCache")

# app.ext.add_dependency(Path, lambda **kwargs: Path(kwargs['path']))
app.config.PATH_STATIC = Path("./static")
app.add_route(static_gzip, "/static/<path:path>")

app.config.BULK = json.loads(Path("bulk.config.json").read_text())


@app.route("/")
async def root(request):
    log.info("root")
    return sanic.response.json(request.app.config.BULK)
