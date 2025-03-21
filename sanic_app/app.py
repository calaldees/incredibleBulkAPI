from pathlib import Path

import sanic
from sanic.log import logger as log

from .static_gzip import static_gzip

app = sanic.Sanic("incredibleBulkAPI")

# Static Gzip
# app.ext.add_dependency(Path, lambda **kwargs: Path(kwargs['path']))
app.config.PATH_STATIC = Path("bulk")
if not app.config.PATH_STATIC.is_dir():
    raise Exception(f'{app.config.PATH_STATIC=} must exist')
app.add_route(static_gzip, "/bulk/<path:str>")

# Root README
app.config.README = Path("README.md").read_text()
@app.route("/")
async def root(request):
    return sanic.response.text(app.config.README)

# app.config.BULK = json.loads(Path("bulk.config.json").read_text())