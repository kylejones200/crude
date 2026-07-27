# Partner Handoff – Crude Assay

**Project:** Crude Assay 
**Focus:** Crude oil quality analysis and dashboards 
**Date:** 2025

---

## Summary

This repo is a **crude-assay** Flask app. It provides:

- Web UI: Crude Assay home, dashboard, and market views
- REST API: Assay health and market-data endpoints
- One main service: `CrudeAssayService` (quality scoring, API gravity, sulfur, regression, etc.)

All other former workflows (trading, finance, MLflow, power, transportation, etc.) have been removed.

---

## Quick Start

```bash
uv sync
uv run python app.py
```

- **App:** http://localhost:8888/ 
- **Health:** http://localhost:8888/health 
- **API info:** http://localhost:8888/api 

---

## What’s Included

| Area | Contents |
|------|----------|
| **App** | `app.py` – registers assay API + assay/crude-assay web blueprints |
| **Routes** | `routes/api/v1/assay.py`, `routes/web/main.py`, `routes/web/assay.py` |
| **Services** | `services/crude_assay_service.py`, `services/compatibility_service.py`, `services/blending_service.py`, `services/domain_adapter.py`, `services/assay/` |
| **Templates** | `base.html`, `_macros.html`, `crude_assay_home.html`, `crude_assay_dashboard.html`, `crude_assay_market.html`, `crude_assay_compatibility.html`, `crude_assay_blending.html` |
| **Core** | `core/` – auth, error_handlers, api_response, rate_limiting, logging, config |
| **Tests** | `tests/test_routes.py`, unit/e2e/integration focused on assay |

---

## Key Files

- **Entry:** `app.py`
- **Assay API:** `routes/api/v1/assay.py`
- **Assay web:** `routes/web/assay.py` (dashboard, market, compatibility, blending), `routes/web/main.py` (/, /crude-assay/)
- **Dashboard data:** `services/crude_assay_service.py` (`get_dashboard_data()`)
- **Config:** `config/development.yml`, `config/production.yml`

---

## API (assay only)

- `GET /api/v1/assay/health` – no auth
- `GET /api/v1/assay/market-data` – requires auth (e.g. `Authorization: Bearer trader-token`)

---

## Testing

```bash
pytest tests/ -v
```

Conftest uses `app.create_app`. Tests cover health, assay API, and web redirects/views.

---

## Deployment

See `DEPLOYMENT.md` for server setup, env vars, and production notes. Docker: `Dockerfile` and `docker-compose.yml` are present and can be adapted for assay-only.