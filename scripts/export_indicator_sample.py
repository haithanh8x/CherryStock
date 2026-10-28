"""Export a small diagnostic sample using the saved Export_Indicator.apx.

Run on Windows with AmiBroker installed:
    python -m scripts.export_indicator_sample --rows 30

The adapter executes the saved APX (ApplyTo=2); this script never writes DuckDB.
It copies a few representative D/W/M rows into a small sample CSV and prints
coverage statistics. The full raw CSV is retained for troubleshooting.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from src.cherrystock.config.settings import settings
from src.cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter
from scripts.sync_amibroker_indicator_full import DEFAULT_AFL, validate_apx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=30)
    parser.add_argument("--output-dir", type=Path, default=Path("data/indicator_sample"))
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be positive")
    validate_apx(DEFAULT_AFL.with_suffix(".apx"), DEFAULT_AFL, incremental=True)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = output_dir / "Export_Indicator_sample_raw.csv"
    sample = output_dir / "Export_Indicator_sample.csv"

    WindowsAmiBrokerAdapter(database_path=settings.amibroker_database_path).run_explore_export(
        formula_path=DEFAULT_AFL,
        export_path=raw,
        apply_to=2,
        range_mode=0,
        range_n=0,
        timeout_seconds=3600.0,
    )
    with raw.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames or []
        if "Ticker" not in columns:
            raise ValueError("Missing Ticker column in APX export")
        d_cols = [c for c in columns if c.endswith("_D")]
        w_cols = [c for c in columns if c.endswith("_W")]
        m_cols = [c for c in columns if c.endswith("_M")]
        if not all((d_cols, w_cols, m_cols)):
            raise ValueError("Expected D/W/M indicator columns; check APX Timeframes=ALL")
        counts = Counter()
        selected = []
        seen_dates = set()
        seen_tickers = set()
        for row in reader:
            counts["rows"] += 1
            ticker = row.get("Ticker", "")
            day = row.get("Date") or row.get("Date/Time") or ""
            seen_dates.add(day)
            seen_tickers.add(ticker)
            has_w = any((row.get(c) or "").strip() not in ("", "Null", "null") for c in w_cols)
            has_m = any((row.get(c) or "").strip() not in ("", "Null", "null") for c in m_cols)
            counts["weekly_rows"] += has_w
            counts["monthly_rows"] += has_m
            # Prioritize sparse weekly/monthly rows in the sample.
            if len(selected) < args.rows:
                selected.append((int(has_w) + 2 * int(has_m), row))
            elif has_w or has_m:
                weakest = min(range(len(selected)), key=lambda i: selected[i][0])
                if int(has_w) + 2 * int(has_m) > selected[weakest][0]:
                    selected[weakest] = (int(has_w) + 2 * int(has_m), row)
    with sample.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(row for _, row in selected)
    print(f"RAW={raw}")
    print(f"SAMPLE={sample}")
    print(f"ROWS={counts['rows']} TICKERS={len(seen_tickers)} DATES={len(seen_dates)}")
    print(f"ROWS_WITH_W={counts['weekly_rows']} ROWS_WITH_M={counts['monthly_rows']}")
    print("NOTE: Weekly/monthly values must be validated against the last trading session of each period.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
