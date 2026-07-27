# Units and solver tolerances

This document defines units, scales, and numerical tolerances used across the `crude` workspace.

## Volumes and rates

| Quantity | Unit | Where used |
|----------|------|------------|
| Crude volume | **barrels (bbl)** | Blend recipes, LP decision variables, purchase/inventory plans |
| Site receipt rate | **bbl/day** | `site_limits.receive_min`, `receive_max` |
| Site charge rate | **bbl/day** | `site_limits.charge_min`, `charge_max` |
| Tank capacity | **bbl** | `site_limits.tank_cap`, `tank_floor` (total across all grades) |
| Monthly receipt/charge caps | **bbl/month** | Computed as `daily_limit × days_in_month` |

Grade-level tank and charge bounds are allocated by slate fraction (e.g. light 40% → 40% of site cap).

## Quality properties

| Property | Unit | Blend rule |
|----------|------|------------|
| API gravity | **degrees API** | Volume-weighted arithmetic mean |
| Sulfur | **wt %** | Volume-weighted arithmetic mean |
| Total acid number (TAN) | **mg KOH/g** | Volume-weighted arithmetic mean |
| SBN / IN | dimensionless | Used in SBN/IN compatibility index only |

## Economics

| Quantity | Unit | Notes |
|----------|------|-------|
| Crude price | **USD/bbl** | Scenario `price_per_bbl` or monthly `brent`/`wti` |
| Objective value | **USD** | Minimize total feed cost (+ unmet-demand penalty for inventory) |
| Unmet demand penalty | **1000 USD/bbl** | `UNMET_DEMAND_PENALTY_USD_PER_BBL` in inventory LP |
| Shadow prices | **USD/bbl** | Marginal objective change per relaxed bbl of capacity |

Live prices come from Yahoo Finance (WTI/Brent spot or daily history).

## Solver

| Setting | Value |
|---------|-------|
| Production LP solver | **microlp** (pure Rust, via `good_lp`) |
| Feasibility tolerance | **1e-3 bbl** on receipt/charge balance checks post-solve |
| Parity objective tolerance | **0.01%** relative (12-month blend), **1 USD** absolute (tiny fixtures) |
| Shadow price bump | **10 bbl/day** receipt/charge, **100 bbl** tank cap (finite-difference) |

Alternative solvers (`highs`, `coin_cbc`) can be evaluated via `good_lp` features but are not enabled in the default build to keep compile times and binary size down.

## Time indexing

| Field | Meaning |
|-------|---------|
| `start_year`, `start_month` | Calendar start of horizon |
| `months` | Number of optimization months (0-indexed in outputs) |
| `month` in plans | 0 = first month; inventory ending month uses `months` |

Lead times (`foreign_m`, `canada_m`, `domestic_m`) are in **whole months** between order and receipt.

## Assay validation bounds

| Field | Valid range | Warning threshold |
|-------|-------------|-------------------|
| API gravity | 10–50 °API | < 15 or > 45 |
| Sulfur | 0–10 wt % | > 5 wt % (sour) |
| TAN | ≥ 0 | missing → warning |
| SBN / IN | optional | missing → warning |

Errors block import; warnings are returned in `AssayImportReport.warnings`.
