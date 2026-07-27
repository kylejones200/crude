# Legacy Python archives

Archived Python repos merged into `crude` in July 2026. **Do not extend these trees** — all active development is in the Rust crates (`crates/`), CLI (`apps/cli/`), and API (`apps/api/`).

| Path | Origin | Notes |
|------|--------|-------|
| [`databricks-assay/`](databricks-assay/) | `assay 2/` (Databricks + regression demo) | Notebooks, Pyomo stubs, HTML demos — reference only |
| [`docs/`](docs/) | `assay/` (Flask repo) | Boundary audit and handoff docs; runnable code was never present locally |

The hollow Flask skeleton (`app.py` without `routes/` / `services/` / `src/`) was removed in July 2026; see [`docs/BOUNDARY.md`](docs/BOUNDARY.md).

Sample CSVs live in [`fixtures/legacy-sample-data/`](../fixtures/legacy-sample-data/) (large PI/Aspen files downsampled to 100 rows). LP parity goldens are in [`fixtures/parity/`](../fixtures/parity/).

See [`INVENTORY.md`](../INVENTORY.md) for the capability migration map.
