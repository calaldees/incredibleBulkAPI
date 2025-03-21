

def register_bulk_data_generator(app: sanic.Sanic):
    app.ctx.BULK_CACHE_OUTPUT_PATH_DATA = Path("cache_bulk_data.json.gz")
    app.ctx.BULK_CACHE_REGEN_PERIOD = datetime.timedelta(hours=1)
    app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD = datetime.timedelta(seconds=10)

    app.add_route(_bulk_data, "/_bulk_data")
    #app.add_route(bulk_data, "/bulk_data")

    setup_background_bulk_generator(
        app,
        endpoint_path="/_bulk_data",
        output_path=app.ctx.BULK_CACHE_OUTPUT_PATH_DATA,
        cache_period=app.ctx.BULK_CACHE_REGEN_PERIOD,
        retry_period=app.ctx.BULK_CACHE_ERROR_RETRY_PERIOD,
        headers={"Accept": "application/vnd.global.5+json"},
    )
