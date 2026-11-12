FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY gateway/pyproject.toml gateway/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway /app/gateway

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
