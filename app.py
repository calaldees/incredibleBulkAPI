import sanic
from sanic.log import logger as log

app = sanic.Sanic("bulkCache")


@app.route("/")
async def root(request):
    log.info("root")
    return sanic.response.json({})
