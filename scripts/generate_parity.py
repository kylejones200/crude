#!/usr/bin/env python3
"""Regenerate parity golden JSON from the Rust optimizer (canonical implementation).

The legacy Python repos were removed in v0.1.0-migration. Use this script only
to refresh fixtures after intentional solver or scenario changes:

    cd crude
    cargo run -- inventory optimize fixtures/scenarios/refinery-inventory.yaml --json
    cargo run -- blend optimize fixtures/scenarios/blend-schedule-tiny.yaml --json
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def run_cli(args: list[str]) -> dict:
    cmd = ["cargo", "run", "--quiet", "--"] + args
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def write_inventory_golden() -> None:
    result = run_cli(
        ["inventory", "optimize", "fixtures/scenarios/refinery-inventory.yaml", "--json"]
    )
    purchase = result["purchase_plan"]
    payload = {
        "scenario": "refinery-inventory",
        "tolerance_objective_pct": 0.01,
        "objective_value_usd": result["objective_value_usd"],
        "status": "optimal",
        "min_purchase_rows": 1,
        "total_purchase_bbl": sum(row["barrels"] for row in purchase),
    }
    out = FIXTURES / "parity" / "inventory-refinery.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {out}")


def write_blend_golden(scenario_yaml: str, parity_name: str, tolerance: float) -> None:
    result = run_cli(["blend", "optimize", f"fixtures/scenarios/{scenario_yaml}", "--json"])
    purchase = result["purchase_plan"]
    payload = {
        "scenario": scenario_yaml.replace(".yaml", ""),
        "objective_value_usd": result["objective_value_usd"],
        "total_purchase_bbl": sum(row["barrels"] for row in purchase),
        "tolerance_objective_pct": tolerance,
        "status": "optimal",
    }
    if "tiny" in scenario_yaml:
        end_inv = next(r for r in result["inventory_plan"] if r["month"] == 1)["inventory"]
        payload["ending_inventory_bbl"] = end_inv
    else:
        payload["purchase_months"] = len({row["month"] for row in purchase})
    out = FIXTURES / "parity" / parity_name
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {out}")


def main() -> None:
    write_inventory_golden()
    write_blend_golden("blend-schedule-tiny.yaml", "blend-schedule-tiny.json", 0.0)
    write_blend_golden("blend-schedule-12month.yaml", "blend-schedule-12month.json", 0.0001)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        sys.exit(exc.returncode)
