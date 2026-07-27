#!/usr/bin/env python3
"""
Generate a multi-year AspenTech planning CSV with thousands of rows.

- Output path: resources/sample_data/aspentech_planning.csv
- Preserves the original columns:
  scenario_id,scenario_name,run_date,planning_period,status,crude_slate_id,
  total_crude_bpd,cdu_throughput_bpd,vdu_throughput_bpd,fcc_throughput_bpd,
  hcu_throughput_bpd,gasoline_production_bpd,diesel_production_bpd,
  fuel_oil_production_bpd,total_margin_usd_day,energy_cost_usd_day,
  variable_cost_usd_day,crude_cost_usd_day,product_revenue_usd_day

We synthesize monthly scenarios across multiple years and several scenario types.
The generator archives the previous CSV to resources/archive/<timestamp>/ before
writing the new dataset.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import shutil

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'resources' / 'sample_data' / 'aspentech_planning.csv'
ARCHIVE_DIR = BASE / 'resources' / 'archive' / datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

# Configuration
YEARS_BACK = 10          # generate roughly 10 years of data
SCENARIOS_PER_MONTH = 36 # number of scenario variants per month (thousands total)
RNG = np.random.default_rng(7)

SCENARIO_TEMPLATES = [
    ('Base_Case',            dict(margin=1.00, diesel=1.00, gasoline=1.00, heavy=1.00)),
    ('High_Crude_Price',     dict(margin=0.92, diesel=0.96, gasoline=0.95, heavy=1.02)),
    ('Max_Diesel_Mode',      dict(margin=1.05, diesel=1.15, gasoline=0.90, heavy=0.95)),
    ('Min_Fuel_Oil',         dict(margin=1.03, diesel=1.02, gasoline=1.02, heavy=0.85)),
    ('Heavy_Crude_Slate',    dict(margin=0.90, diesel=0.98, gasoline=0.90, heavy=1.20)),
    ('Light_Sweet_Slate',    dict(margin=1.12, diesel=0.98, gasoline=1.10, heavy=0.80)),
    ('Coker_Max_Run',        dict(margin=1.02, diesel=1.04, gasoline=0.98, heavy=1.10)),
    ('Product_Demand_High',  dict(margin=1.08, diesel=1.06, gasoline=1.08, heavy=0.95)),
]

CRUDES = ['SLATE_A','SLATE_B','SLATE_C','SLATE_D','SLATE_E','SLATE_F']


def month_range(end: datetime, years_back: int):
    # inclusive months from end going backwards years_back
    end_month = datetime(end.year, end.month, 1, tzinfo=end.tzinfo)
    months = []
    total_months = years_back * 12
    for i in range(total_months):
        # previous month by subtracting i months
        year = end_month.year
        month = end_month.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append(datetime(year, month, 1, tzinfo=end.tzinfo))
    return list(reversed(months))


def gen_for_month(month_dt: datetime):
    # baseline capacities
    total_crude = RNG.integers(130_000, 180_000)
    cdu = int(total_crude * RNG.uniform(0.9, 1.0))
    vdu = int(total_crude * RNG.uniform(0.35, 0.55))
    fcc = int(total_crude * RNG.uniform(0.25, 0.40))
    hcu = int(total_crude * RNG.uniform(0.15, 0.30))

    base_gasoline = int(total_crude * RNG.uniform(0.40, 0.50))
    base_diesel   = int(total_crude * RNG.uniform(0.32, 0.42))
    base_fuel     = int(total_crude * RNG.uniform(0.08, 0.14))

    rows = []
    for idx in range(SCENARIOS_PER_MONTH):
        name, weights = SCENARIO_TEMPLATES[idx % len(SCENARIO_TEMPLATES)]
        crude_slate = RNG.choice(CRUDES)
        # slight random noise month-to-month
        g = int(base_gasoline * weights['gasoline'] * RNG.uniform(0.95, 1.05))
        d = int(base_diesel   * weights['diesel']   * RNG.uniform(0.95, 1.05))
        f = int(base_fuel     * weights['heavy']    * RNG.uniform(0.95, 1.05))

        # economics
        crude_cost   = int(total_crude * RNG.uniform(70, 95) * 30)  # rough monthly crude cost
        energy_cost  = int(total_crude * RNG.uniform(2.3e3, 3.5e3))
        variable_cost= int(total_crude * RNG.uniform(1.8e3, 2.6e3))
        product_rev  = int(g * RNG.uniform(95, 115) + d * RNG.uniform(95, 110) + f * RNG.uniform(70, 90))
        total_margin = int(product_rev - crude_cost - energy_cost - variable_cost)
        total_margin = int(total_margin * weights['margin'])

        run_date = month_dt + timedelta(days=int(RNG.integers(0, 27)), hours=int(RNG.integers(0, 23)))
        scenario_id = f"ASP_{month_dt.year % 100:02d}{month_dt.month:02d}_{idx+1:02d}"
        scenario_name = f"{name}_{month_dt.strftime('%b%Y')}"
        period = month_dt.strftime('%b%Y')

        rows.append(dict(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            run_date=run_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            planning_period=period,
            status='Optimal',
            crude_slate_id=crude_slate,
            total_crude_bpd=total_crude,
            cdu_throughput_bpd=cdu,
            vdu_throughput_bpd=vdu,
            fcc_throughput_bpd=fcc,
            hcu_throughput_bpd=hcu,
            gasoline_production_bpd=g,
            diesel_production_bpd=d,
            fuel_oil_production_bpd=f,
            total_margin_usd_day=total_margin,
            energy_cost_usd_day=energy_cost,
            variable_cost_usd_day=variable_cost,
            crude_cost_usd_day=crude_cost,
            product_revenue_usd_day=product_rev,
        ))
    return rows


def main():
    now = datetime.now(timezone.utc)
    months = month_range(now, YEARS_BACK)
    all_rows = []
    for m in months:
        all_rows.extend(gen_for_month(m))
    df = pd.DataFrame(all_rows)
    # Archive existing file
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        shutil.copy2(OUT, ARCHIVE_DIR / OUT.name)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} rows to {OUT}")

if __name__ == '__main__':
    main()
