FROM python:alpine as base
    RUN apk add --no-cache \
        make \
    && true
    WORKDIR /app/

ENV PYTHONPATH=/site-packages

FROM base as python_dependencies
    COPY ./pyproject.toml ./
    RUN pip install --no-cache-dir -e . -t /site-packages
    ENV PYTHONPATH=/site-packages
FROM python_dependencies as python_dependencies_test
    RUN pip install --no-cache-dir -e '.[test]' -t /site-packages

FROM python_dependencies as code
    COPY . .

FROM code as test
    COPY --from=python_dependencies_test /site-packages /site-packages
    #COPY ./tests ./tests
    #RUN python3 -m pytest -x
    #RUN python3 -m mypy .

FROM code as production
    EXPOSE 8000
    CMD ["python3", "-m", "sanic", "--host", "0.0.0.0", "sanic_app.app:app", "--debug"]
    # "--single-process"
