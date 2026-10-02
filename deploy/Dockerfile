FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first so code edits don't invalidate this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/ app/
COPY static/ static/
COPY seed/ seed/

RUN useradd --system --uid 1000 --home /app app \
    && mkdir -p /app/data && chown app:app /app/data
USER app

ENV PATH="/app/.venv/bin:$PATH" DB_PATH=/app/data/school.db
EXPOSE 8000

# Exactly one worker: the per-IP rate limiter lives in process memory.
# The app is only reachable through Caddy on the compose network, so trusting its
# X-Forwarded-For is safe.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
