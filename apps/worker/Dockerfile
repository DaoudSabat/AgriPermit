FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc postgresql-client libpq-dev && rm -rf /var/lib/apt/lists/*

COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/worker /app
COPY packages /packages

ENV PYTHONPATH=/app:/packages

CMD ["celery", "-A", "celery_app", "worker", "--loglevel=info"]
