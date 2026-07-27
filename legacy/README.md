# Legacy Python archives

Archived Python repos merged into `crude` in July 2026. **Do not extend these trees** — all active development is in the Rust crates (`crates/`), CLI (`apps/cli/`), and API (`apps/api/`).

| Directory | Origin | Notes |
|-----------|--------|-------|
| [`python-assay/`](python-assay/) | `assay/` (Flask web app skeleton) | UI and routes superseded by `crude-api`; domain logic ported to Rust |
| [`databricks-assay/`](databricks-assay/) | `assay 2/` (Databricks + regression demo) | Lakehouse, notebooks, Pyomo stubs — reference only; LP parity lives in `fixtures/parity/` |

Sample CSVs from the Databricks repo are in [`fixtures/legacy-sample-data/`](../fixtures/legacy-sample-data/).

See [`INVENTORY.md`](../INVENTORY.md) for the capability migration map and deletion gates.
