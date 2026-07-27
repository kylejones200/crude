# Legacy sample data

CSV and JSON fixtures from the archived Databricks crude-assay repo (`legacy/databricks-assay/`). Used for demos, notebook replay, and future assay corpus expansion.

| File | Description |
|------|-------------|
| `assays.csv` | 49 crude assays (API, sulfur, cut yields) |
| `seasonal_prices.csv` | Monthly price series by crude |
| `blend_supply.csv` | Blend supply constraints |
| `market_summary.json` | Market snapshot |
| `pi_system_data.csv` | PI historian-style telemetry (large) |
| `aspentech_planning.csv` | AspenTech planning export (large) |

For Rust parity tests, prefer [`../parity/`](../parity/) and [`../scenarios/`](../scenarios/).
