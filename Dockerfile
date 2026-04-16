# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip build \
    && pip install --no-cache-dir -e . \
    && pip wheel --no-cache-dir --wheel-dir /wheels -e .

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: run as non-root
RUN groupadd -r tgai && useradd -r -g tgai -d /app -s /sbin/nologin tgai

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /wheels /wheels
COPY --from=builder /app /app

RUN pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

# Data directory with correct ownership
RUN mkdir -p /data/sessions && chown -R tgai:tgai /data

USER tgai

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/data/data.db \
    SESSION_PATH=/data/sessions/

VOLUME ["/data"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio, aiosqlite; asyncio.run(aiosqlite.connect('/data/data.db'))" || exit 1

CMD ["tgai-agent"]
