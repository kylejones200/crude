# Deployment – Crude Assay

## Prerequisites
- Python 3.11+
- Redis (optional, for caching)
- Nginx (recommended for production)

---

## Quick deploy

```bash
# App directory
cd /opt/assay # or your path

# Install uv (https://docs.astral.sh/uv/), then:
uv sync
# Or with a system Python venv:
# python3.11 -m venv venv && source venv/bin/activate && pip install -e . gunicorn
```

## Environment

```bash
cp .env.example .env
# Set: SECRET_KEY, FLASK_PORT (default 8888), FLASK_DEBUG=False for prod
# Optional: REDIS_URL, DATABASE_URL if you add persistence
```

## Run

**Development:**
```bash
python app.py
```

**Production (Gunicorn):**
```bash
uv run gunicorn -w 4 -b 127.0.0.1:8888 "app:create_app"
```
(Or activate venv and run the same gunicorn command.)

## Systemd (optional)

If using **uv**, the virtualenv is usually `.venv`. If using a classic venv, replace `.venv` with `venv` below.

```ini
[Unit]
Description=Crude Assay
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/assay
Environment="PATH=/opt/assay/.venv/bin"
ExecStart=/opt/assay/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8888 "app:create_app"
Restart=always

[Install]
WantedBy=multi-user.target
```

## Nginx

Proxy to `http://127.0.0.1:8888`; serve `/static` from app static folder if desired. Use `/health` for health checks.

## Docker

```bash
docker build -t crude-assay .
docker run -p 8888:8888 crude-assay
```

The Dockerfile already uses `app:create_app` via gunicorn `--factory app:create_app`.
