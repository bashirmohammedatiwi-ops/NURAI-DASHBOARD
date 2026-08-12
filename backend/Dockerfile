FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=8s --retries=5 \
  CMD curl -f http://127.0.0.1:9000/health/ready || exit 1

CMD ["sh", "-c", "python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 9000"]
