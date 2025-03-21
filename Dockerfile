FROM python:alpine

RUN apk add --no-cache \
    make \
&& true

WORKDIR /app/

COPY ./pyproject.toml .
RUN pip install --no-cache-dir -e '.[test]' -t /site-packages
ENV PYTHONPATH=/site-packages

COPY . .

# python3 -m sanic --host 0.0.0.0 --single-process app --debug
CMD ["python3", "-m", "sanic", "--host", "0.0.0.0", "--single-process", "sanic_app.app", "--debug"]

# TODO: Production build with CMD and without [test]
