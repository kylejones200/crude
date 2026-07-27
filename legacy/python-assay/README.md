# Crude Assay

**Crude oil assay analytics: quality scoring, API gravity, sulfur content, and dashboard.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

---

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install & Run

```bash
cd /path/to/assay
uv sync
uv run python app.py
```

Without uv: create a venv, then `pip install -e .` from the project root (dependencies are in `pyproject.toml`).

### Access
- **Home:** http://localhost:8888/
- **Dashboard:** http://localhost:8888/assay/dashboard
- **Market:** http://localhost:8888/assay/market
- **Blending:** http://localhost:8888/assay/blending
- **Compatibility:** http://localhost:8888/assay/compatibility
- **Health:** http://localhost:8888/health
- **API info:** http://localhost:8888/api

`/crude-assay/` and `/assay/` redirect to `/`.

---

## Features

- **Crude Assay Dashboard** – Quality scoring, API gravity, sulfur, processing index, regression analysis
- **Market** – WTI/Brent and assay market view
- **Blending** – Blend optimization (backed by `blending_service`)
- **Compatibility** – Blend compatibility (backed by `compatibility_service`)
- **Assay API** – `/api/v1/assay/health`, `/api/v1/assay/market-data` (auth required)

---

## Domain / App separation

**Separation is done when** the blend optimization route or service calls `domain_pkg.api.run_blend_optimization` and all boundary tests still pass. See **BOUNDARY.md** for the full definition of done and how to prove it in code.

---

## Project Structure

```
assay/
├── app.py # Entry point: create_app(), registers API + web blueprints
├── pyproject.toml
├── uv.lock
├── .env.example
├── routes/
│ ├── api/v1/assay.py # Assay REST API (/api/v1/assay/*)
│ └── web/
│ ├── main.py # /, /crude-assay/ redirect
│ └── assay.py # /assay/dashboard, market, blending, compatibility
├── core/ # Auth, errors, logging, rate limiting, config
├── services/
│ ├── crude_assay_service.py # Dashboard & market metrics
│ ├── compatibility_service.py
│ ├── blending_service.py # Web blend form → domain_adapter
│ ├── domain_adapter.py # Single adapter to domain_pkg.api
│ └── assay/ # Assay parsers, EIA, market data, blend_solver, etc.
├── src/
│ ├── domain_pkg/ # Pure domain: api, blend_optimizer, contracts, etc.
│ └── app_pkg/ # CLI, pipelines, plots (optional)
├── templates/ # base, crude_assay_*
├── static/
│ ├── css/
│ └── js/main.js
├── tests/
└── config/ # development.yml, production.yml
```

---

## API

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | No | App health |
| `GET /api` | No | API info |
| `GET /api/v1/assay/health` | No | Assay service health |
| `GET /api/v1/assay/market-data` | Yes | Assay market data (WTI, Brent, etc.) |

**Auth (development):** `Authorization: Bearer admin-token` or `trader-token` or `analyst-token`.

---

## Tests

```bash
pytest tests/ -v
pytest tests/test_routes.py -v
```

### Domain boundary (no Databricks)

Domain tests run on a laptop with no Spark, DBFS, or network. App must import only `domain_pkg.api`.

```bash
# Smoke: domain surface importable
uv run python -c "from domain_pkg.api import run_blend_optimization; print('ok')"

# Boundary + behavior
uv run pytest tests/domain/ -v
```

See **BOUNDARY.md** for the full definition of done and testable conditions.

---

## Configuration

- `config/development.yml` – Dev settings
- `config/production.yml` – Production
- `.env` / `.env.example` – `FLASK_PORT`, `SECRET_KEY`, etc.

---

## License

Proprietary
