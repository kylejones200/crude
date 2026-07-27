# Phase 1: Consolidation Inventory

Replacement merge for crude oil blending repositories. Default decision: **Delete**.

Duplicate folders (`crude-assay 2`, `crude-blending 2`, etc.) are copies — inventory once, delete all copies together.

## Winner Selection

| Capability | Winner | Source | Losers |
|------------|--------|--------|--------|
| Canonical crude model | `crude-domain` (new Rust) | User spec + `contracts.py` field names | All Python dataclasses |
| Assay parser | `crude-assay` | `crude-assay/services/assay/assay_parser.py` | `real_assay_service.py` stubs |
| Assay normalization | `crude-assay` | New normalizer (was missing in Python) | — |
| Blend property calculation | `crude-blending` | Volume-weighted linear blend | UI heuristics in Next.js |
| Constraint evaluation | `crude-constraints` | `blend_optimizer.py` quality bounds + `compatibility_service.py` SBN/IN | `risk_limits.py`, Pyomo constraints |
| Economic model | `crude-economics` | `blend_solver._calculate_value` heuristic + feed cost | `pnl_calculator.py`, trading MTM |
| Optimization model | `crude-optimization` | `blend_optimizer.py` + `inventory_optimization.py` | Pyomo duplicates |
| Scenario format | `crude-scenarios` | New YAML contract (user spec) | All legacy JSON/form/API payloads |
| Persistence format | `crude-storage` | JSON run records | Delta Lake, SQLAlchemy ORM, Streamlit cache |

## crude-assay

| Capability | File | Keep | Rewrite | Delete | Reason |
|------------|------|:----:|:-------:|:------:|--------|
| Contracts | `src/domain_pkg/contracts.py` | ✓ | | | Ported to `crude-domain` |
| Blend LP | `src/domain_pkg/blend_optimizer.py` | ✓ | | | Quality constraint logic ported |
| Inventory LP | `src/domain_pkg/inventory_optimization.py` | ✓ | | | Phase 4 |
| Policy | `src/domain_pkg/policy.py` | ✓ | | | Defaults in Rust constants |
| Compatibility | `services/compatibility_service.py` | ✓ | | | SBN/IN ported |
| Assay parser | `services/assay/assay_parser.py` | ✓ | | | JSON/XLSX/PDF text extraction ported |
| Domain adapter | `services/domain_adapter.py` | | | ✓ | Replaced by CLI |
| Crude assay service | `services/crude_assay_service.py` | | | ✓ | Fixtures only |
| Monte Carlo | `services/assay/monte_carlo.py` | ✓ | | | GBM in `crude-scenarios` |
| Price service | `services/assay/real_price_service.py` | ✓ | | | Yahoo fetch in `crude-economics` |
| EIA connector | `services/assay/eia_connector.py` | | ✓ | | Phase 4 |
| Legacy blend solver | `services/assay/blend_solver.py` | | | ✓ | Duplicate LP |
| Pyomo modules | `services/assay/core/optimization/*` | | | ✓ | Duplicate |
| Scenario engine | `services/assay/scenario_engine.py` | | | ✓ | Broken ORM imports |
| PnL / risk | `services/assay/pnl_calculator.py`, `risk_limits.py` | | | ✓ | Trading boilerplate |
| Flask routes/UI | `routes/`, `templates/`, `static/` | | | ✓ | UI excluded |
| App infra | `core/`, `config/` | | | ✓ | Not domain |

## crude-blending

Nearly identical to crude-assay. Same winners. Additionally delete:

| Capability | File | Delete | Reason |
|------------|------|:------:|--------|
| Enterprise duplicate | `src/crude_optimizer/core/optimization.py` | ✓ | Duplicate of domain_pkg |
| Lakehouse | `src/crude_optimizer/lakehouse/*` | ✓ | Databricks-only; not in scope |
| Frontend | `frontend/` | ✓ | UI excluded |
| Gasoline LP stubs | `services/blending_service.py` SUNCO constants | | ✓ | Textbook demo, no solver |

## crude-inventory-optimizer

| Capability | File | Keep | Rewrite | Delete | Reason |
|------------|------|:----:|:-------:|:------:|--------|
| Inventory LP | `app/core/optimization.py` | | ✓ | | Phase 4; broken indentation |
| Price service | `app/services/price_service.py` | | ✓ | | Phase 4 |
| Lakehouse schemas | `app/lakehouse/schema_definitions.py` | | ✓ | | Reference only |
| Monte Carlo | `app/core/simulation.py` | | ✓ | | Phase 4 |
| Next.js UI | `crude-optimizer-nextjs/` | | | ✓ | UI excluded; blend formulas extracted |
| Duplicates | `optimization_v2.py`, `.dist_workspace/` | | | ✓ | Redundant |

## crude_optimizer 2

| Capability | File | Keep | Rewrite | Delete | Reason |
|------------|------|:----:|:-------:|:------:|--------|
| Inventory LP | `optimization_model.py` | | ✓ | | Phase 4; best Python inventory LP |
| Price service | `services/price_service.py` | | ✓ | | Phase 4 |
| Monte Carlo | `services/optimization_service.py` | | ✓ | | Phase 4 |
| Golden artifacts | `test_optimization_results/*` | ✓ | | | Parity fixtures Phase 5 |
| Streamlit | `app.py`, `streamlit_app.py`, `pages/` | | | ✓ | UI excluded |
| Duplicates | `optimization_v2.py`, `optimization_service_v2.py` | | | ✓ | Broken/redundant |

## Deletion Gate Status

| Repository | Unique logic migrated | Parity tested | Fixtures moved | Workflows clear | CLI replaces main job |
|------------|----------------------|---------------|----------------|-----------------|----------------------|
| crude-assay | Yes | Yes | Yes | Manual | Yes |
| crude-blending | Yes | Yes | Yes | Manual | Yes |
| crude-inventory-optimizer | Yes | Yes | Yes | Manual | Yes |
| crude_optimizer 2 | Yes | Yes | Partial | Manual | Yes |

## Deleted (Phase 6 partial)

- `crude-assay 2/` — duplicate copy removed
- `crude-blending 2/` — duplicate copy removed
- `crude-inventory-optimizer 2/` — duplicate copy removed
- `crude_optimizer/` — empty stub removed

Primary repos were deleted July 2026 after the Rust port passed parity gates. Legacy Streamlit goldens live in `crude/fixtures/parity/legacy-streamlit/`.

## Merged into `crude/` (July 2026 workspace cleanup)

Local `assay/` and `assay 2/` folders were consolidated into this repo:

| Source | Destination | Notes |
|--------|-------------|-------|
| `assay/` (Flask skeleton + docs) | removed | Hollow skeleton and handoff docs deleted; migration map in this file |
| `assay 2/` (Databricks + regression) | removed | Databricks archive deleted July 2026; sample CSVs in `fixtures/legacy-sample-data/` |
| `assay 2/resources/sample_data/` | `fixtures/legacy-sample-data/` | 49-crude CSV corpus + PI/Aspen samples |

## Cleanup (July 2026)

- Removed hollow `legacy/python-assay/` (empty `routes/`, `services/`, `src/`)
- Downsampled `fixtures/legacy-sample-data/pi_system_data.csv` and `aspentech_planning.csv` to 101 rows
- Removed unused `fixtures/parity/legacy-streamlit/optimization_*.lp` and `.mps` artifacts
- Removed `legacy/databricks-assay/` (Databricks notebooks, regression demos, lakehouse stubs)
- Removed `legacy/docs/` handoff notes (superseded by this inventory and `README.md`)
