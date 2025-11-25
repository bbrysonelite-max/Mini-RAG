FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser $APP_HOME && \
    mkdir -p /app/logs /app/out /app/backups /app/var && \
    chown -R appuser:appuser /app/logs /app/out /app/backups /app/var

USER appuser

EXPOSE 8000

# Railway uses $PORT env var; fallback to 8000 for local Docker
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}

