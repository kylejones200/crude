# crude

Single Rust repository for crude oil assay import, blending, constraint evaluation, and feed-cost optimization.

## Install

**Prebuilt binary** (see [GitHub Releases](https://github.com/kylejones200/crude/releases)):

```bash
gh release download v0.1.0 --repo kylejones200/crude --pattern 'crude-macos-arm64' -O crude
chmod +x crude
./crude doctor
```

**From source:**

```bash
cargo install --git https://github.com/kylejones200/crude --tag v0.1.0 crude-cli
# or
git clone https://github.com/kylejones200/crude.git && cd crude
cargo build --release
```

## Structure

```text
crude/
├── crates/          # domain, assay, blending, optimization, scenarios, storage, doctor
├── apps/cli/        # `crude` binary
├── apps/api/        # axum HTTP API on :8080
├── fixtures/        # scenarios, parity goldens, assay samples, legacy-sample-data
├── legacy/          # archived Python repos (Flask + Databricks) — reference only
├── schemas/         # JSON Schema for scenario YAML contracts
├── docs/units.md    # units, tolerances, validation bounds
└── tests/           # parity, vertical path, benchmarks
```

## CLI

```bash
# Assay import (returns warnings on stderr; full report with --json)
cargo run -- assay import fixtures/assays/wti.json
cargo run -- assay import fixtures/assays/wti-assay-table.txt --json

# Blend evaluation and multi-month schedule LP
cargo run -- blend evaluate fixtures/blends/gulf-coast-blend.yaml
cargo run -- blend optimize fixtures/scenarios/blend-schedule-tiny.yaml

# Static single-period optimization
cargo run -- optimize fixtures/scenarios/gulf-coast-slate.yaml

# Inventory procurement (multi-month LP)
cargo run -- inventory optimize fixtures/scenarios/refinery-inventory.yaml

# SBN/IN compatibility, prices, Monte Carlo
cargo run -- compatibility fixtures/compatibility/sample.json
cargo run -- prices fetch --history 2y
cargo run -- simulate fixtures/prices/wti-sample.json

# Runs, health, benchmarks
cargo run -- runs list
cargo run -- compare runs/*.json
cargo run -- doctor
cargo run -- doctor --online
cargo run -- benchmark
```

## API

```bash
cargo run -p crude-api
# GET  /health  /doctor  /benchmark/lp  /prices/fetch  /runs
# POST /assay/import  /blend/evaluate  /optimize  /inventory/optimize
#      /blend/schedule/optimize  /compatibility/evaluate  /compare  /simulate
```

## Tests

```bash
cargo test --workspace
cargo test --test benchmarks -- --ignored   # LP timing report
python3 scripts/generate_parity.py         # refresh parity goldens from Rust
```

## Documentation

- [`ROADMAP.md`](ROADMAP.md) — phases and milestones
- [`docs/units.md`](docs/units.md) — units and solver tolerances
- [`INVENTORY.md`](INVENTORY.md) — capability inventory from legacy repos
