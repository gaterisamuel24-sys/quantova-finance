# syntax=docker/dockerfile:1
# Production image: builds the frontend, then runs the API, which also serves the app.
# Build from the repository root:  docker build -t quantova .

# ── 1. Frontend build ──────────────────────────────────
FROM node:26-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Empty: the app calls the API on its own origin (/api), so no API address is baked in.
ENV VITE_API_BASE_URL=""
RUN npm run build

# ── 2. Python dependencies ─────────────────────────────
FROM python:3.14-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first (cached while only app code changes), exactly as locked, no dev tools.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --locked --no-dev

# ── 3. Runtime ─────────────────────────────────────────
FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    FRONTEND_DIST_DIR=/app/frontend_dist \
    ENVIRONMENT=production \
    LOG_FORMAT=json \
    CORS_ORIGINS=[]
WORKDIR /app
COPY --from=backend-build /app /app
COPY --from=frontend /build/dist /app/frontend_dist
# A dedicated user with no login shell and no write access to the code.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin quantova
USER quantova
EXPOSE 8000
# --proxy-headers: take the visitor's address from the platform's proxy (X-Forwarded-For).
# Trusting any forwarder is safe only because the container is reachable solely through
# that proxy, which is the case on Render. PORT is set by the platform.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
