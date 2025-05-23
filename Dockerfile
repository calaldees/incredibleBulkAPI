FROM python:alpine AS base
    RUN apk add --no-cache \
        make \
    && true
    WORKDIR /app/

ENV PYTHONPATH=/site-packages

FROM base AS python_dependencies
    COPY ./pyproject.toml ./
    RUN pip install --no-cache-dir -e . -t /site-packages
    ENV PYTHONPATH=/site-packages
FROM python_dependencies AS python_dependencies_test
    RUN pip install --no-cache-dir -e '.[test]' -t /site-packages

FROM python_dependencies AS code
    COPY . .

FROM code AS test
    COPY --from=python_dependencies_test /site-packages /site-packages
    COPY ./tests ./tests
    RUN python3 -m pytest -x
    #RUN python3 -m mypy .

FROM code AS production
    EXPOSE 8000
    CMD ["python3", "-m", "sanic", "--host", "0.0.0.0", "sanic_app.app:app", "--single-process"]
