# syntax=docker/dockerfile:1.7
# Multi-stage build: node compiles frontend → python runtime serves API + frontend/dist.

# ============================================================
# Stage 1 — frontend build
# ============================================================
FROM node:22-alpine AS frontend-builder

RUN corepack enable && corepack prepare pnpm@11.5.2 --activate

WORKDIR /build

# Lockfile-first install for layer caching
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Build
COPY frontend/ ./
RUN pnpm build

# ============================================================
# Stage 2 — python runtime
# ============================================================
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app

# Dependencies (cached layer)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Source
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

# Install project (editable so __file__ resolves to /app/src/... — required for
# analytis.api.main:create_app() path math that locates frontend/dist relative to source)
RUN uv sync --frozen --no-dev

# Frontend dist (backend mounts /app/frontend/dist as static)
COPY --from=frontend-builder /build/dist ./frontend/dist

ENV PATH="/app/.venv/bin:$PATH"

# Verify backend's path math finds frontend/dist (fails build if uv installed
# the package non-editable and __file__ resolves to .venv/site-packages).
RUN python -c "from pathlib import Path; import analytis.api.main as m; \
    p = Path(m.__file__).resolve().parents[3] / 'frontend' / 'dist' / 'index.html'; \
    assert p.exists(), f'frontend dist not findable from analytis.api.main: {p}'; \
    print(f'OK frontend dist at {p}')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/v1/health || exit 1

CMD ["uvicorn", "analytis.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
