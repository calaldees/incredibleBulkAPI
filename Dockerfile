FROM python:alpine

RUN apk add --no-cache \
    make \
&& true

WORKDIR /app/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /site-packages
ENV PYTHONPATH=/site-packages

COPY . .

# python3 -m sanic --host 0.0.0.0 --single-process app --debug
CMD ["python3", "-m", "sanic", "--host", "0.0.0.0", "--single-process", "src.app", "--debug"]
