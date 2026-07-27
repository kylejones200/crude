# crude

Single Rust repository for crude oil assay import, blending, constraint evaluation, and feed-cost optimization.

Replacement merge — not a compatibility layer. All Python repositories in `cude/` are slated for deletion once parity is proven.

## Structure

```text
crude/
├── crates/
│   ├── domain/           # Canonical Crude, Assay, BlendRecipe types
│   ├── assay/            # JSON/YAML/Excel/PDF import + normalization
│   ├── blending/         # Volume-weighted blend properties
│   ├── constraints/      # Product specs + SBN/IN compatibility
│   ├── economics/        # Feed cost, value heuristics, live prices
│   ├── optimization/     # Static blend LP, blend schedule LP, inventory LP
│   ├── scenarios/        # YAML scenario contract
│   └── storage/          # JSON run persistence
├── apps/
│   ├── cli/
│   └── api/              # axum HTTP API on :8080
├── fixtures/
├── tests/
├── INVENTORY.md          # Phase 1 capability inventory + deletion gates
└── ROADMAP.md            # Forward plan (phases, milestones, backlog)
```

## CLI

```bash
cargo build --release

# Assay import
cargo run -- assay import fixtures/assays/wti.json

# Blend evaluation
cargo run -- blend evaluate fixtures/blends/gulf-coast-blend.yaml

# Multi-month blend schedule LP
cargo run -- blend optimize fixtures/scenarios/blend-schedule-tiny.yaml

# Static single-period optimization
cargo run -- optimize fixtures/scenarios/gulf-coast-slate.yaml

# Inventory procurement (multi-month LP)
cargo run -- inventory optimize fixtures/scenarios/refinery-inventory.yaml

# SBN/IN compatibility
cargo run -- compatibility fixtures/compatibility/sample.json

# Live WTI/Brent spot (cached 24h in ~/.cache/crude/)
cargo run -- prices fetch
cargo run -- prices fetch --history 2y -o fixtures/prices/wti-brent-2y.json

# List saved runs
cargo run -- runs list
cargo run -- runs show run-1234567890

# Health check (solver + fixtures)
cargo run -- doctor
cargo run -- doctor --online   # also hits Yahoo Finance

# Compare runs
cargo run -- compare runs/*.json
```

## Scenario contract

See `fixtures/scenarios/gulf-coast-slate.yaml` for the canonical input format.

## Tests

```bash
cargo test --workspace
```

## Migration status

See [`ROADMAP.md`](ROADMAP.md) for the full forward plan. Consolidation summary:

- Phase 1 (inventory): `INVENTORY.md`
- Phase 2 (spine): complete
- Phase 3 (vertical path): complete — assay → blend → constraints → optimize
- Phase 4 (inventory + Monte Carlo + blend schedule): complete
- Phase 5 (parity): inventory LP + blend schedule tiny match Python golden
- Phase 6: duplicate `* 2` folders deleted; primary repos remain until deletion gate
