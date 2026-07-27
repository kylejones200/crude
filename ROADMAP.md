# crude — Project Roadmap

**Last updated:** July 2026  
**Status:** v0.1.0 shipped; hardening complete through Phase 4

---

## Vision

One Rust codebase for crude oil assay handling, blend evaluation, and procurement optimization — replacing four fragmented Python repos with a single CLI-first tool and a thin HTTP API.

**Principles**

- One winner per capability (no compatibility shims, no duplicate solvers)
- Canonical domain types: `Crude`, `Assay`, `BlendRecipe`, `BlendComponent`
- YAML scenario contracts for all optimization jobs
- Parity-tested against legacy golden outputs
- No UI, lakehouse, or trading boilerplate in scope unless explicitly added later

---

## Where we are today

| Area | Status | Notes |
|------|--------|-------|
| Domain model | Done | `crude-domain` |
| Assay import + validation report | Done | JSON, YAML, Excel, PDF/text tables; warnings vs errors |
| Blend properties | Done | Volume-weighted linear + proptest |
| Product + SBN/IN constraints | Done | CLI + API `compatibility` |
| Static / schedule / inventory LP | Done | microlp; shadow prices via sensitivity |
| Monte Carlo + live prices | Done | GBM; Yahoo with disk cache |
| CLI + API | Done | All workflows; doctor, compare, benchmark |
| Storage + run metadata | Done | Unified `RunRecord` |
| CI + release binaries | Done | v0.1.0 on GitHub Releases |
| Docs | Done | `docs/units.md`, JSON schemas |

**Test coverage:** 35+ workspace tests (unit, integration, parity, property).

---

## Phase 0 — Consolidation *(complete)*

| Task | Status |
|------|--------|
| Delete legacy Python repos | Done |
| Archive golden artifacts | Done |
| Top-level `cude/` README | Done |
| `v0.1.0-migration` tag | Done |

---

## Phase 1 — Hardening *(complete)*

### 1.1 Solver & optimization

- [x] Production solver: **microlp** (benchmark harness in `crude-doctor`; see `docs/units.md`)
- [x] Infeasibility diagnostics (preflight + post-solve hints)
- [x] Shadow prices on inventory and blend schedule outputs
- [x] 12-month blend schedule parity fixture
- [x] CI (`cargo test`, `clippy`, `fmt`)

### 1.2 Assay pipeline

- [x] PDF/text table extraction (tab, pipe, whitespace columns + key-value)
- [x] `AssayImportReport` with warnings vs errors
- [x] Golden table fixture: `fixtures/assays/wti-assay-table.txt`

### 1.3 Economics & prices

- [x] Historical price series + disk cache

### 1.4 Storage & runs

- [x] Unified `RunRecord`, compare, metadata (solver, version, git commit)

### 1.5 CLI polish

- [x] `--json` / `--quiet`, exit codes, `doctor`, `benchmark`

---

## Phase 2 — API & integration *(complete)*

All CLI workflows available over HTTP:

| Endpoint | Status |
|----------|--------|
| `POST /assay/import` | Done — returns `AssayImportReport` |
| `POST /blend/evaluate` | Done |
| `POST /blend/schedule/optimize` | Done |
| `POST /optimize` | Done |
| `POST /inventory/optimize` | Done |
| `POST /compatibility/evaluate` | Done |
| `GET /prices/fetch` | Done |
| `GET /runs`, `GET /runs/{id}` | Done |
| `GET /doctor` | Done |
| `GET /benchmark/lp` | Done |
| `POST /compare` | Done |
| `POST /simulate` | Done |

---

## Phase 3 — Distribution *(complete)*

- [x] `cargo install --git https://github.com/kylejones200/crude --tag v0.1.0 crude-cli`
- [x] GitHub release binaries (Linux x86_64, macOS arm64/x86_64)
- [x] Versioned scenario schemas in `schemas/`
- PyPI wrapper: **deferred** — use native binary or `cargo install`

---

## Phase 4 — Quality *(complete)*

- [x] CI green on every push
- [x] Parity suite: inventory, blend tiny/12-month, legacy Streamlit CSV/summary, golden JSON validation
- [x] LP benchmark harness (`crude benchmark`, `GET /benchmark/lp`, `tests/benchmarks.rs`)
- [x] Property tests on blend linearity (proptest)
- [x] `docs/units.md` — units, tolerances, validation bounds
- [x] `scripts/generate_parity.py` — refresh goldens from Rust CLI

---

## Phase 5 — Future capabilities *(backlog only)*

Pursue only with a concrete workflow need:

| Idea | Notes |
|------|-------|
| Distillation yield optimization | New LP formulation |
| Crude compatibility matrix | Batch SBN/IN over assay library |
| Scenario bundles | Multi-scenario sensitivity |
| WASM blend evaluate | Browser calculator |
| Lakehouse export | Parquet run history |
| HiGHS/CBC solver feature flag | Optional `good_lp` backend for dual values |

---

## Milestones

| Milestone | Status |
|-----------|--------|
| **M0: Migration closed** | Done (`v0.1.0-migration`) |
| **M1: v0.1.0** | Done — [release](https://github.com/kylejones200/crude/releases/tag/v0.1.0) |
| **M2: API complete** | Done |
| **M3: v1.0.0** | Next — broader assay corpus, optional alternate solver |

---

## Commands

```bash
cargo test --workspace
cargo run -- assay import fixtures/assays/wti-assay-table.txt
cargo run -- blend optimize fixtures/scenarios/blend-schedule-tiny.yaml
cargo run -- inventory optimize fixtures/scenarios/refinery-inventory.yaml
cargo run -- doctor
cargo run -- benchmark
cargo run -- compare runs/*.json
```

See [`README.md`](README.md) and [`docs/units.md`](docs/units.md).
