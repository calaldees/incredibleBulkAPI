FROM python:alpine

RUN apk add --no-cache \
    make \
&& true

WORKDIR /app/

COPY ./pyproject.toml .
RUN pip install --no-cache-dir -e '.[test]' -t /site-packages
ENV PYTHONPATH=/site-packages

COPY . .

CMD ["python3", "-m", "sanic", "--host", "0.0.0.0", "sanic_app.app:app", "--debug"]
# "--single-process"

# TODO: Production build with CMD and without [test]
