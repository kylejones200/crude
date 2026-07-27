# Multi-stage Docker build for production deployment
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install uv and system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Production stage: use pyproject.toml + uv.lock
FROM base as production

WORKDIR /app

# Install dependencies with uv (no dev)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Install app in editable form and gunicorn for serving
RUN uv pip install -e . gunicorn

COPY --chown=app:app . .

USER app
RUN mkdir -p /app/logs

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/health', timeout=10)" || exit 1

EXPOSE 8888

CMD ["gunicorn", "--bind", "0.0.0.0:8888", "--workers", "4", "--worker-class", "sync", "--timeout", "30", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "--factory", "app:create_app"]
