# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq5 \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

ENV CACHE_BUST=20261109_v7
WORKDIR /app

# Copy application
RUN echo "bust_20261110_v23"
COPY . /app
COPY run.py /app/run.py

# Create directories (will be properly owned at runtime by entrypoint)
RUN mkdir -p /app/logs /app/data
RUN echo "bust_ep_20261110_v23"

# Copy entrypoint script and set permissions
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose healthcheck port if needed (bot is purely polling / async worker)
EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
