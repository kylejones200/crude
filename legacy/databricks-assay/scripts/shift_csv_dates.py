#!/usr/bin/env python3
"""
Shift timestamp columns in CSVs to the trailing 30 days window.

- bliss_blend_recipes.csv: column created_date
- haverly_optimization.csv: column run_timestamp
- lims_quality_tests.csv: column test_date

Strategy:
- Parse each file, detect min/max of the target column
- Linearly map the original date range to [now-30d, now], preserving relative ordering
- If the original range is a single timestamp (min==max), map all rows to evenly spaced times in last 24h ending now
- Write back with ISO8601 UTC (Z) timestamps
"""
import sys
from pathlib import Path
import shutil
import pandas as pd
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parents[1] / 'resources' / 'sample_data'
NOW = datetime.now(timezone.utc)
START = NOW - timedelta(days=30)
ARCHIVE_DIR = (Path(__file__).resolve().parents[1] / 'resources' / 'archive' / NOW.strftime('%Y%m%d_%H%M%S'))

TARGETS = [
    (BASE / 'bliss_blend_recipes.csv', 'created_date'),
    (BASE / 'haverly_optimization.csv', 'run_timestamp'),
    (BASE / 'lims_quality_tests.csv', 'test_date'),
    (BASE / 'aspentech_planning.csv', 'run_date'),
]

def map_to_window(ts_series: pd.Series) -> pd.Series:
    s = pd.to_datetime(ts_series, utc=True, errors='coerce')
    if s.isna().all():
        return s
    smin, smax = s.min(), s.max()
    if pd.isna(smin) or pd.isna(smax):
        return s
    if smin == smax:
        # Single instant: spread across last 24h
        n = len(s)
        base = NOW - timedelta(hours=24)
        return pd.to_datetime([base + i * (timedelta(hours=24) / max(1, n-1)) for i in range(n)], utc=True)
    # Linear map to [START, NOW]
    total = (smax - smin).total_seconds()
    span = (NOW - START).total_seconds()
    rel = (s - smin).dt.total_seconds()  # seconds from min
    scaled_seconds = rel / total * span
    mapped = START + pd.to_timedelta(scaled_seconds, unit='s')
    return pd.to_datetime(mapped, utc=True)


def process_file(path: Path, col: str):
    if not path.exists():
        print(f"WARN: file not found {path}")
        return
    # Archive original file before modifying
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, ARCHIVE_DIR / path.name)
    
    df = pd.read_csv(path)
    if col not in df.columns:
        print(f"WARN: column {col} not in {path.name}")
        return
    new_col = map_to_window(df[col])
    # Format with Z suffix
    df[col] = new_col.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    df.to_csv(path, index=False)
    print(f"Updated {path.name}: {len(df)} rows; range {df[col].min()} .. {df[col].max()}")


def main():
    for path, col in TARGETS:
        process_file(path, col)

if __name__ == '__main__':
    main()
