# crude — Product Roadmap (2026–2028)

**Last updated:** July 2026  
**Current release:** v0.1.0  
**Horizon:** 18–24 months (H2 2026 → H2 2028)

---

## Product vision

**crude** is the decision engine for refinery crude procurement and blending: import assays, evaluate blend quality and compatibility, and optimize multi-month purchase and inventory plans under real constraints — with reproducible runs, parity-tested math, and a CLI-first workflow that teams can wire into planners, data pipelines, or internal tools.

**Who it's for**

| Persona | Job | crude helps by… |
|---------|-----|-----------------|
| Crude scheduler / planner | Build monthly crude slate and tank inventory | Inventory and blend-schedule LP, shadow prices, scenario YAML |
| Assay analyst | Normalize lab and vendor assay data | Import pipeline, validation report, canonical `Crude` model |
| Process engineer | Check blend feasibility before scheduling | SBN/IN compatibility, product property bounds |
| Quant / automation | Embed optimization in scripts and services | JSON CLI, HTTP API, versioned schemas, run records |

**Principles** (unchanged)

- One winner per capability — no duplicate solvers or compatibility shims
- YAML scenario contracts for every optimization job
- Parity-tested against recorded goldens before behavior changes ship
- Lakehouse, trading MTM, and generic UI boilerplate stay out of scope unless a concrete workflow demands them

---

## Where we are (v0.1.0)

Shipped and stable:

- Domain model, assay import (JSON/YAML/Excel/PDF text), blend evaluation, SBN/IN compatibility
- Static, blend-schedule, and inventory LPs (microlp); shadow prices; infeasibility hints
- Monte Carlo price simulation; Yahoo fetch with disk cache
- CLI + axum API covering all workflows; run storage and compare
- CI, release binaries, JSON schemas, `docs/units.md`, 35+ tests

See git tags `v0.1.0` and `v0.1.0-migration` for the consolidation baseline.

---

## Roadmap overview

```text
2026 H2          2027 H1          2027 H2          2028 H1          2028 H2
────────         ────────         ────────         ────────         ────────
v1.0 GA          Assay corpus     Planning depth   Distribution     Advanced LP
Solver upgrade   EIA + premiums   Scenario packs   WASM + Parquet   Yields / multi-site
Assay library    Compat matrix    Distillation?    PyPI wrapper     Hosted API (opt)
```

| Milestone | Target | Outcome |
|-----------|--------|---------|
| **M3: v1.0.0** | Q4 2026 | Production-grade GA for procurement LP workflows |
| **M4: Assay platform** | Q2 2027 | Curated corpus + batch import; analyst-ready reports |
| **M5: Planning suite** | Q4 2027 | Multi-scenario sensitivity and compatibility at scale |
| **M6: v2.0** | Q2 2028 | Embeddable engine + export paths for data platforms |
| **M7: Advanced formulations** | Q4 2028 | Yield-aware and multi-asset extensions (if validated need) |

---

## H2 2026 — Production GA (v1.0.0)

**Theme:** Make v0.1.0 safe to depend on in daily planning loops.

### Assay & data quality

- [ ] Expand fixture corpus from `fixtures/legacy-sample-data/assays.csv` to ≥20 JSON assays with regression tests per property
- [ ] Batch import: `crude assay import-dir` with consolidated report
- [ ] Document validation bounds and unit conventions in operator-facing guide (extend `docs/units.md`)

### Solver & optimization

- [ ] Optional **HiGHS** backend (`good_lp` feature flag) for improved dual values and large schedules
- [ ] LP benchmark gates in CI (regression on solve time for 12-month fixtures)
- [ ] Clearer infeasibility narratives tied to constraint IDs in JSON output

### Operations

- [ ] Semver policy and changelog
- [ ] `crude doctor` checks for schema version, solver backend, and fixture smoke tests
- [ ] Release pipeline: signed binaries + container image for `crude-api`

**Exit criteria for v1.0.0:** 12-month blend and refinery inventory scenarios solve in CI with parity tolerances; alternate solver optional; documented upgrade path from v0.1.0.

---

## H1 2027 — Assay platform & market data

**Theme:** Become the canonical assay library for the team's crude slate.

### Assay library

- [ ] `crude library list|show|validate` over a directory or manifest YAML
- [ ] Assay diff report (property deltas, classification change sweet/sour, light/heavy)
- [ ] Intertek/LIMS-style column mapping from CSV templates (`fixtures/legacy-sample-data/` patterns)

### Economics

- [ ] **EIA** price connector (deferred from legacy inventory) with same cache pattern as Yahoo
- [ ] Quality premium curves from assay properties (API/sulfur → $/bbl adjustment)
- [ ] Scenario YAML fields for freight and regional differentials

### Compatibility at scale

- [ ] **Compatibility matrix** CLI: batch SBN/IN over N crudes → heatmap JSON/CSV
- [ ] Pairwise blend screening before full LP (preflight for schedule scenarios)

**Exit criteria:** Planner can maintain a slate library, run a compatibility matrix, and feed premiums into inventory LP without hand-editing JSON.

---

## H2 2027 — Planning depth

**Theme:** Answer "what if?" faster than rebuilding spreadsheets.

### Scenario workflows

- [ ] **Scenario bundles**: run N YAML scenarios (price shocks, supply loss, quality drift) → summary table
- [ ] `crude compare` enhancements: objective delta, purchase mix shift, binding constraints
- [ ] Sensitivity hooks: ±10% price / demand sweeps with ranked drivers

### Formulations (prioritize by refinery feedback)

- [ ] **Distillation yield optimization** LP (new formulation) — only after v1.0 parity discipline extended to yields
- [ ] Tank turnover and min-run-length soft constraints in inventory model
- [ ] Multi-grade product slate (not just crude grades) as optional scenario block

### Export & observability

- [ ] **Parquet export** of run history (`crude runs export --format parquet`)
- [ ] Structured logging trace IDs on API for audit

**Exit criteria:** Scheduler runs a bundle of 5+ scenarios in one command and exports results for downstream BI without custom scripts.

---

## H1 2028 — Distribution & embeddability (v2.0)

**Theme:** crude runs everywhere the planner works — terminal, notebook, browser snippet, pipeline.

### Distribution

- [ ] **PyPI wrapper** (`pip install crude-cli`) delegating to native binary or wasm stub
- [ ] `cargo install` stable channel aligned with GitHub releases
- [ ] Minimal **WASM** crate: blend evaluate + compatibility in browser (no full LP in wasm v1)

### API & integration

- [ ] OpenAPI spec generated from axum routes; versioned `/v1/` prefix
- [ ] Auth middleware pattern (API key) for `crude-api` deployments
- [ ] Webhook or poll endpoint for long-running optimize jobs

### Data platform hooks

- [ ] DuckDB / Polars example notebooks reading Parquet run exports
- [ ] Scenario validation CLI against JSON Schema (`crude validate scenario.yaml`)

**Exit criteria:** External team can embed blend evaluate via WASM or HTTP without cloning the full repo; run history lands in analytics stores in one step.

---

## H2 2028 — Advanced optimization (conditional)

**Theme:** Stretch capabilities — only where validated with refinery or trading partners.

Pursue items below only after M6 ships and a named workflow owner signs off:

| Capability | Depends on | Notes |
|------------|------------|-------|
| Multi-refinery / multi-site procurement | Scenario schema v2 | Shared crude pool, site-specific demand |
| Stochastic programming layer | Scenario bundles + MC | Two-stage purchase under price uncertainty |
| Nonlinear blend properties | Domain model extension | Iterative LP or dedicated MINLP (explicit scope) |
| Regression-based quality scores | New model, not legacy ML archive | Quality index as LP constraint input |
| Hosted managed API | Auth, quotas, SLOs | Optional product line; not default open-source scope |

**Exit criteria for v2.x:** At least one advanced formulation has parity fixtures and does not regress core LP paths.

---

## Explicitly out of scope (24 months)

Unless requirements change with a named sponsor:

- Databricks / Delta Lake pipelines (removed from repo July 2026)
- Flask/Streamlit dashboards and partner handoff UI
- Trading PnL, MTM, and risk limits
- Gasoline blend or non-crude feed optimization
- Real-time SCADA / PI historian ingestion

---

## Success metrics

| Metric | v1.0 target | v2.0 target |
|--------|-------------|-------------|
| Core LP scenarios with parity tests | 4 | 8+ |
| Curated assay fixtures | 20+ | 50+ |
| CI solve time (12-month schedule) | < 2s on CI runner | < 1s |
| API endpoints with OpenAPI docs | 0 | 100% |
| External installs (cargo + binary + pip) | 2 channels | 3 channels |

---

## Completed history (pre-2026 H2)

| Phase | Status |
|-------|--------|
| Phase 0 — Consolidation | Done |
| Phase 1 — Hardening | Done |
| Phase 2 — API & integration | Done |
| Phase 3 — Distribution (partial; PyPI deferred) | Done |
| Phase 4 — Quality | Done |
| Legacy Python / Databricks archive | Removed July 2026 |

Detail: [`INVENTORY.md`](INVENTORY.md)

---

## How to use this roadmap

1. Pick the **current half** and work top-down within theme boundaries.
2. Do not start H2 2028 items until M3 (v1.0) exit criteria are met.
3. Any formulation change ships with parity fixtures or an explicit waiver in `CHANGELOG.md`.
4. Update this file at each milestone tag.

```bash
cargo test --workspace
cargo run -- doctor
cargo run -- blend optimize fixtures/scenarios/blend-schedule-12month.yaml
```

See also [`README.md`](README.md) and [`docs/units.md`](docs/units.md).
