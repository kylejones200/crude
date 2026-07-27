#!/usr/bin/env python3
"""
Generate exactly 10,000 PI datapoints ending at 'now' and write to
resources/sample_data/pi_system_data.csv.

We simulate 18 signals per timestamp step:
- For each of 5 tanks (TK101..TK105; WTI, BRENT, MAYA, ARB, URALS):
  - LEVEL (PCT), TEMP (DEGF), VOLUME (BBL)
- Three unit tags:
  - CDU_FEED_RATE (BPD), CDU_FEED_TEMP (DEGF), VDU_FEED_RATE (BPD)

10,000 rows / 18 signals ≈ 556 timestamp steps. We create a time grid
of 556 points uniformly over the last 30 days, ending at 'now'.

The script archives the previous CSV to resources/archive/<timestamp>/
before overwriting.
"""
from pathlib import Path
import shutil
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / 'resources' / 'sample_data'
OUT_PATH = DATA_DIR / 'pi_system_data.csv'
NOW = datetime.now(timezone.utc)
START = NOW - timedelta(days=30)
ARCHIVE_DIR = BASE / 'resources' / 'archive' / NOW.strftime('%Y%m%d_%H%M%S')

TARGET_ROWS = 10000
SIGNALS_PER_STEP = 18  # 5 tanks * 3 + 3 unit tags
STEPS = int(np.ceil(TARGET_ROWS / SIGNALS_PER_STEP))  # 556

rng = np.random.default_rng(42)

def simulate_frame() -> pd.DataFrame:
    idx = pd.date_range(start=START, end=NOW, periods=STEPS, tz='UTC')
    tanks = [
        ('TK101', 'WTI'),
        ('TK102', 'BRENT'),
        ('TK103', 'MAYA'),
        ('TK104', 'ARB'),
        ('TK105', 'URALS'),
    ]
    rows = []
    for tank, crude in tanks:
        base_level = rng.uniform(60, 90)
        level = (
            base_level
            + 10 * np.sin(np.linspace(0, 8 * np.pi, len(idx)))
            + rng.normal(0, 1.0, len(idx))
        )
        temp = 85 + 10 * np.sin(np.linspace(0, 2 * np.pi, len(idx))) + rng.normal(0, 0.5, len(idx))
        volume = np.clip(level, 0, 100) * rng.uniform(450, 550)  # bbl
        for ts, lv, tp, vol in zip(idx, level, temp, volume):
            rows.append((ts, f"{tank}_LEVEL", float(np.clip(lv, 0, 100)), 'PCT', 'Good', tank, crude))
            rows.append((ts, f"{tank}_TEMP", float(tp), 'DEGF', 'Good', tank, crude))
            rows.append((ts, f"{tank}_VOLUME", float(vol), 'BBL', 'Good', tank, crude))
    # unit/feed
    unit_tags = [
        ('CDU001', 'BLEND_A', 'CDU_FEED_RATE', 45000, 5000, 'BPD'),
        ('CDU001', 'BLEND_A', 'CDU_FEED_TEMP', 480, 10, 'DEGF'),
        ('VDU001', 'BLEND_B', 'VDU_FEED_RATE', 18500, 2500, 'BPD'),
    ]
    for unit, blend, tag, base, amp, unit_str in unit_tags:
        signal = base + amp * np.sin(np.linspace(0, 6 * np.pi, len(idx))) + rng.normal(0, amp * 0.05, len(idx))
        for ts, val in zip(idx, signal):
            rows.append((ts, tag, float(max(0, val)), unit_str, 'Good', unit, blend))
    df = pd.DataFrame(rows, columns=['timestamp','tag_name','value','unit','quality','crude_tank','crude_id'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    # Sort and trim to exactly TARGET_ROWS
    df.sort_values(['timestamp','tag_name'], inplace=True, kind='mergesort')
    if len(df) > TARGET_ROWS:
        df = df.iloc[-TARGET_ROWS:]  # keep the most recent subset
    return df

def main():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        shutil.copy2(OUT_PATH, ARCHIVE_DIR / OUT_PATH.name)
    df = simulate_frame()
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")

if __name__ == '__main__':
    main()
