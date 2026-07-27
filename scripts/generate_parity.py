#!/usr/bin/env python3
"""Generate parity golden values from crude-assay domain_pkg (canonical Python)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSAY = ROOT.parent / "crude-assay"
sys.path.insert(0, str(ASSAY / "src"))

from domain_pkg.inventory_optimization import run_inventory_optimization  # noqa: E402
from domain_pkg.contracts import SiteLimits, LeadTimes  # noqa: E402


def refinery_inventory_golden() -> dict:
    limits = SiteLimits(
        receive_min=50,
        receive_max=1000,
        charge_min=50,
        charge_max=500,
        tank_cap=100000,
        tank_target=20000,
        tank_risk=10000,
        tank_floor=500,
    )
    lt = LeadTimes(foreign_m=2, canada_m=1, domestic_m=1)
    prices = pd.DataFrame([{"brent": 78 + i, "wti": 74 + i} for i in range(6)])
    result = run_inventory_optimization(
        2025,
        1,
        6,
        limits,
        lt,
        {"light": 20000, "medium": 20000, "heavy": 20000},
        prices,
        {"light": 40, "medium": 35, "heavy": 25},
    )
    return {
        "scenario": "refinery-inventory",
        "success": result.success,
        "objective_value_usd": result.objective_value,
        "solver_status": result.solver_status,
        "total_purchase_bbl": sum(r["barrels"] for r in result.purchase_plan),
        "purchase_rows": len(result.purchase_plan),
    }


def main() -> None:
    golden = refinery_inventory_golden()
    out = ROOT / "fixtures" / "parity" / "inventory-refinery.json"
    payload = {
        "scenario": golden["scenario"],
        "tolerance_objective_pct": 0.001,
        "objective_value_usd": golden["objective_value_usd"],
        "status": "optimal",
        "min_purchase_rows": 1,
        "total_purchase_bbl": golden["total_purchase_bbl"],
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(golden, indent=2))


if __name__ == "__main__":
    main()
