# Repo Audit – Crude Assay (Second Pass)

**Date:** After simplification (single entry point, api/ and services/assay/ removed, core/container removed).

---

## 1. Entry point & app

| Item | Status |
|------|--------|
| Single `create_app()` | Only `app.py`; no second factory |
| Docker / tests / script | All use `app:create_app` |
| API registration | Direct: `app.register_blueprint(assay_api_bp)` from `routes.api.v1` |
| Web blueprints | `main_web_bp`, `assay_web_bp` only; `/crude-assay/` redirect on main |

**Verdict:** Clean.

---

## 2. Routes

| Area | Status |
|------|--------|
| **routes/api/v1/** | `assay.py` defines `assay_api_bp`; `__init__.py` exports it |
| **routes/api/__init__.py** | Empty (just docstring). Harmless; can stay or be removed |
| **routes/web/** | `main.py` (/, /crude-assay), `assay.py` (dashboard, market, compatibility, blending) |
| **routes/schemas/** | **Removed.** Package was unused; deleted to avoid dead code. |

**Verdict:** Clean.

---

## 3. Services

| File | Used by |
|------|--------|
| `crude_assay_service.py` | `routes/web/assay.py` |
| `compatibility_service.py` | `routes/web/assay.py` |
| `blending_service.py` | `routes/web/assay.py` |

**Verdict:** All three services are used; no dead code.

---

## 4. Core

| Module | Used by app/routes | Used by tests | Notes |
|--------|--------------------|---------------|--------|
| `error_handlers` | app.py | — | |
| `logging` | app.py | — | |
| `api_response` | (via error_handlers, auth, rate_limiting) | — | |
| `auth` | routes/api/v1/assay.py | — | |
| `rate_limiting` | routes/api/v1/assay.py | — | |
| `config` | — | conftest, unit/test_config.py | |
| `cache` | — | unit/test_cache.py | |
| `config_loader` | — | — | Only in its own `if __name__ == "__main__"` (config summary script). Not used by app. |
| `exceptions` | (via error_handlers, api_response, etc.) | — | |
| `validation` | (via api_response.ValidationError) | — | |
| `events` | — | — | Module exists; no longer exported from `core/__init__.py` (leaner public API). |
| `interfaces` | — | — | Module exists; no longer exported from `core/__init__.py` (leaner public API). |
| `decorators` | — | — | core.decorators exports `cached`, `timed`, `logged`, `validated`. Only `core.cache` uses `@cached` (and tests use core.cache). So decorators are used indirectly via cache, not directly by app |

**Verdict:** 
- **Used by app:** error_handlers, logging, api_response, auth, rate_limiting, exceptions, validation; cache used by tests. 
- **Trimmed:** core/__init__.py does not export events or interfaces (not in __all__). Those modules remain on disk for possible future use.

---

## 5. Templates & static

| Item | Status |
|------|--------|
| Templates | All 6 referenced templates exist: base, crude_assay_home, crude_assay_dashboard, crude_assay_market, crude_assay_compatibility, crude_assay_blending; _macros.html for includes |
| **static/css/** | app.css (placeholder); Tailwind via CDN in base.html |
| **static/js/** | `static/js/main.js` added (minimal placeholder). base.html and verify_routes.py both reference it; no 404. |

**Verdict:** Consistent.

---

## 6. Config & docs

| Item | Status |
|------|--------|
| config/development.yml, production.yml | Present; config_loader and core.config can use them |
| .env.example | Present |
| README.md | Project Structure and services list updated (routes, services/, src/, static/js). |
| PROJECT_STRUCTURE.md | Updated: no routes/schemas; core export note; services/assay, domain_adapter, src/; static/js/main.js. |
| AUDIT.md | This file |
| DEMO_GUIDE.md, DEPLOYMENT.md, PARTNER_HANDOFF.md | Not re-audited; assume still useful |

**Verdict:** Docs aligned with current layout.

---

## 7. Tests

- **conftest:** Uses `app.create_app` and `core.config` (ConfigManager, Environment). 
- **test_routes, e2e, integration, unit:** No references to removed api/ or services/assay/ or core.container. 

**Verdict:** Test layout matches simplified app.

---

## Summary

| Category | Result |
|----------|--------|
| Entry point & app | Clean, single factory |
| Routes | Clean; routes/schemas removed |
| Services | All used |
| Core | Public API trimmed (events/interfaces no longer exported) |
| Templates | All exist |
| Static | static/js/main.js present |
| Docs | README and PROJECT_STRUCTURE updated |

**Quick wins completed:**

1. **static/js/main.js** – Added minimal placeholder; no 404. 
2. **README.md** – Project Structure and services updated. 
3. **routes/schemas** – Removed (unused). 
4. **core** – `core/__init__.py` no longer exports `events` or `interfaces`.

No critical issues; repo in good shape.
