# Project Structure – Crude Assay

```
assay/
│
├── app.py # Single entry point: create_app(), registers API + web blueprints
├── pyproject.toml
├── uv.lock
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── AUDIT.md # Repo audit and simplification notes
│
├── routes/
│ ├── api/
│ │ └── v1/
│ │ ├── __init__.py # assay_api_bp
│ │ └── assay.py # /api/v1/assay/*
│ └── web/
│ ├── __init__.py # main_web_bp, assay_web_bp
│ ├── main.py # /, /crude-assay/ redirect
│ └── assay.py # /assay/, /assay/dashboard, /assay/market, /assay/compatibility, /assay/blending
│
├── core/
│ ├── api_response.py
│ ├── auth.py
│ ├── cache.py
│ ├── config.py
│ ├── config_loader.py
│ ├── decorators.py
│ ├── error_handlers.py
│ ├── events.py # Not exported from core (unused by app)
│ ├── exceptions.py
│ ├── interfaces.py # Not exported from core (unused by app)
│ ├── logging.py
│ ├── rate_limiting.py
│ ├── utils.py
│ └── validation.py
│
├── services/
│ ├── __init__.py
│ ├── crude_assay_service.py # Dashboard data, quality metrics, regression
│ ├── compatibility_service.py
│ ├── blending_service.py # Web blend form → domain_adapter
│ ├── domain_adapter.py # Single adapter to domain_pkg.api
│ └── assay/ # Assay parsers, EIA, market data, blend_solver, etc.
│
├── src/
│ ├── domain_pkg/ # Pure domain: api, blend_optimizer, contracts, etc.
│ └── app_pkg/ # CLI, pipelines, plots (optional)
│
├── templates/
│ ├── base.html
│ ├── _macros.html
│ ├── crude_assay_home.html
│ ├── crude_assay_dashboard.html
│ ├── crude_assay_market.html
│ ├── crude_assay_compatibility.html
│ └── crude_assay_blending.html
│
├── static/
│ ├── css/
│ └── js/
│ └── main.js
│
├── tests/
│ ├── conftest.py # Uses app.create_app
│ ├── test_routes.py
│ ├── unit/
│ ├── integration/
│ └── e2e/
│
├── config/
│ ├── development.yml
│ └── production.yml
│
└── data/ # (optional; trading data files removed)
```

Removed for crude-assay focus: analytics/, data_ingestion/, data_access/, non-assay routes, non-assay services, non-assay templates, spark_config, trading data JSONs. Removed routes/schemas (unused). Core public API trimmed to config, exceptions, logging, decorators, utils.
