FROM python:alpine

WORKDIR /app/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /site-packages
ENV PYTHONPATH=/site-packages

COPY . .

CMD ["python3", "-m", "sanic", "--host", "0.0.0.0", "--single-process", "app", "--debug"]
