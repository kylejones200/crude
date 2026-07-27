# Definition of Done: Domain / App Separation

Separation is done when every execution path calls `domain_pkg.api` for decisions, when `domain_pkg` imports no Databricks or plotting code, and when domain tests run without Databricks.

---

## Testable conditions

These are enforced by tests and scripts. If any check fails, the boundary is broken.

### 1. App imports one surface

- **Rule:** The app imports `domain_pkg.api` and nothing else from `domain_pkg`.
- **Check:** No file in app surface (e.g. `app.py`, `routes/`, `core/`, `services/`, `scripts/*.py` at repo root) may do `from domain_pkg.contracts import ...` or `from domain_pkg.blend_optimizer import ...` or any submodule other than `api`.
- **Test:** `tests/domain/test_app_imports_only_api.py::test_app_imports_only_domain_api`.

### 2. Domain imports no app / infra

- **Rule:** The domain imports no app code. The domain imports no Databricks, Spark, MLflow, HTTP, or plotting modules.
- **Check:** No file under `src/domain_pkg/` imports `matplotlib`, `plotly`, `streamlit`, `dash`, `dbutils`, `pyspark`, `databricks`, `mlflow`, `delta`, `sqlalchemy`, `requests`, `flask`, `fastapi`.
- **Test:** `tests/domain/test_domain_boundary.py::test_domain_does_not_import_app_only_modules`.

### 3. Domain runs without Databricks

- **Rule:** You can run `pytest` on a laptop. Tests cover the core path. Tests need no Spark session, no DBFS paths, no network.
- **Check:** `pytest tests/domain/` passes with no Spark/Databricks/network. Domain tests use only in-process fixtures.
- **Test:** All tests in `tests/domain/`.

### 4. Domain owns decisions

- **Rule:** Every rule, threshold, scoring step, and transformation lives in `domain_pkg`. The app owns orchestration only.
- **Check:** No policy, scoring, or feature logic in `routes/`, `core/`, or `scripts/`; it lives in `domain_pkg` and is called via `domain_pkg.api`.

### 5. Inputs and outputs explicit

- **Rule:** Domain entrypoints accept dataclasses or plain dicts plus arrays/DataFrames. Domain entrypoints return typed results. The app never reaches into domain internals for intermediate state.
- **Check:** API in `domain_pkg.api` has clear function signatures and return types (e.g. `BlendOptimizationResult`).

### 6. Scripts thin

- **Rule:** `scripts/` contains only “read, call, write, plot.” No math, no feature engineering, no policy, no model logic.
- **Check:** Scripts import `domain_pkg.api`, call one or two entrypoints, then I/O and optional plotting.

### 7. Plots in app only

- **Rule:** Chart code lives in app only. Domain returns numbers and frames. App turns them into figures.
- **Check:** No `matplotlib`/`plotly` in `src/domain_pkg/`; chart code in `src/app_pkg/plots/` or equivalent.

### 8. Backend thin

- **Rule:** Backend routes call `domain_pkg.api`. Backend handles auth, request parsing, and response shape. Backend does not compute health scores or blend logic.
- **Check:** Routes in `routes/` delegate pipeline and health/blend logic to `domain_pkg.api`.

### 9. Dependency graph clean

- **Rule:** The domain package depends on core libs only. The app can depend on Databricks libs. You can install domain with minimal extras.
- **Check:** `src/domain_pkg/` uses only stdlib + typing, dataclasses, numpy, pandas, scipy, sklearn, pulp (or similar); no flask, pyspark, mlflow.

### 10. At least one execution path uses domain API

- **Rule:** At least one top-level route or service calls the domain via the adapter (which calls `domain_pkg.api.run_blend_optimization`).
- **Current path:** `POST /api/v1/assay/blend-optimize` → adapter → `run_blend_optimization`. Integration test in `tests/app/test_blend_route_uses_domain_api.py` proves it.

### 11. Smoke check passes

- **Rule:** One command proves the boundary.
- **Command:** (use `uv run` so the installed package is on the path)
 ```bash
 uv run python -c "from domain_pkg.api import run_blend_optimization; print('ok')"
 ```
- **Or:** `uv run pytest tests/domain/test_domain_boundary.py::test_smoke_import -v`

### 12. Behavior check passes

- **Rule:** One small fixture through the domain yields stable output. A snapshot test is acceptable.
- **Test:** `tests/domain/test_blend_optimization.py` (tiny fixture; optional snapshot of `BlendOptimizationResult` when PuLP available).

---

## One-line summary (for README)

> **Separation is done when** the blend optimization route or service calls `domain_pkg.api.run_blend_optimization` and all boundary tests still pass.

(Cutover complete: at least one top-level execution path uses the domain API.)

## Named path (cutover complete)

- **Path:** `POST /api/v1/assay/blend-optimize` → `routes.api.v1.assay.blend_optimize()` → `services.domain_adapter.run_blend_optimization_adapter()` → `domain_pkg.api.run_blend_optimization()`.
- **Adapter:** `services/domain_adapter.py` (only place in app that imports `domain_pkg.api`). No other `domain_pkg.*` imports in app code.
- **Integration test:** `tests/app/test_blend_route_uses_domain_api.py` (patch adapter and assert route calls domain once; assert response shape).

---

## Proving it

```bash
# Smoke: domain surface importable
uv run python -c "from domain_pkg.api import run_blend_optimization; print('ok')"

# Boundary: domain imports no app-only modules
uv run pytest tests/domain/test_domain_boundary.py -v

# Behavior: core path with fixture (no Spark, no network)
uv run pytest tests/domain/test_blend_optimization.py tests/domain/test_contracts_and_api.py -v

# Full domain tests (no Databricks)
uv run pytest tests/domain/ -v
```

---

## App switch (when you do it)

- **App switch complete:** `app.py` and every entrypoint use `from domain_pkg.api import run_blend_optimization, validate_prices, ...`. The app calls those functions. Outputs match within a chosen tolerance.
- **Scripts trimmed:** `scripts/` holds only I/O and orchestration. Pure logic lives in domain. Duplicate logic removed.
- **Backend switch optional:** If you have Flask (or FastAPI) routes, they call `domain_pkg.api` for pipeline and health/blend logic. Databricks I/O stays outside the domain.
