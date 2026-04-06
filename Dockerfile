# Stage 1: Build dependencies with uv
FROM ghcr.io/astral-sh/uv:latest AS uv

# Stage 2: Install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml ./

RUN uv sync --frozen --no-dev --no-install-project

# Stage 3: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv

COPY apps ./apps
COPY alembic.ini ./
COPY alembic ./alembic

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appgroup /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn voiceagent_api.app:app --app-dir apps/api/src --host 0.0.0.0 --port 8000"]
