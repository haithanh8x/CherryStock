"""Profile Price Movement Character refresh: time each stage and log slow tickers.

Usage:
    python scripts\prof_price_movement_timing.py [--mode full|incremental] [--limit N]
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.domain.analytics.price_movement.runtime import (  # noqa: E402
    calculate_ticker_movement_fast,
)
from cherrystock.domain.analytics.price_movement.source_quality import (  # noqa: E402
    inspect_price_source_quality,
)
from cherrystock.infrastructure.database.repositories.price_movement_repository import (  # noqa: E402
    PriceMovementRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("full", "incremental"), default="full")
    parser.add_argument("--limit", type=int, default=0, help="only profile first N tickers (sorted)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    con = duckdb.connect(settings.local_db_path, read_only=True)
    config = PriceMovementRepository(con).load_enabled_config()
    print(f"[{time.perf_counter() - t0:8.2f}s] config loaded: {config.config_id} {config.model_code} {config.model_version}")

    # Same source view the pipeline uses (load_price_movement_source -> vw_Ticker_OHLC_D)
    t = time.perf_counter()
    source = con.execute(
        """
        SELECT * FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
        """
    ).df()
    print(f"[{time.perf_counter() - t0:8.2f}s] source loaded: {len(source):,} rows in {time.perf_counter() - t:.2f}s")

    tickers = sorted(source["Ticker"].unique().tolist())
    if args.limit > 0:
        tickers = tickers[: args.limit]
    print(f"Tickers to process: {len(tickers)}")

    stage_times = {"inspect": 0.0, "calc": 0.0}
    slow: list[tuple[float, str, int]] = []
    total_events = 0
    total_daily = 0

    t = time.perf_counter()
    for i, ticker in enumerate(tickers, 1):
        ticker_frame = source.loc[source["Ticker"] == ticker].copy()

        t1 = time.perf_counter()
        _ = inspect_price_source_quality(ticker_frame)
        t_inspect = time.perf_counter() - t1

        t1 = time.perf_counter()
        events, daily = calculate_ticker_movement_fast(
            ticker_frame, ticker=ticker, config=config, prior_swings=[], seed_state=None
        )
        t_calc = time.perf_counter() - t1

        stage_times["inspect"] += t_inspect
        stage_times["calc"] += t_calc
        total_events += len(events)
        total_daily += len(daily)
        if t_calc > 1.0:
            slow.append((t_calc, ticker, len(ticker_frame)))

        if i % 50 == 0 or i == len(tickers):
            print(
                f"[{time.perf_counter() - t0:8.2f}s] progress {i}/{len(tickers)} "
                f"(inspect {stage_times['inspect']:.1f}s, calc {stage_times['calc']:.1f}s)"
            )
            sys.stdout.flush()

    print("\n=== Summary ===")
    print(f"Total elapsed:        {time.perf_counter() - t0:.2f}s")
    print(f"Source load:          part of elapsed above")
    print(f"Inspect stage total:  {stage_times['inspect']:.2f}s")
    print(f"Calc stage total:     {stage_times['calc']:.2f}s")
    print(f"Events: {total_events:,}  Daily rows: {total_daily:,}")
    if slow:
        slow.sort(reverse=True)
        print("\nSlowest tickers (calc > 1s):")
        for t_calc, ticker, rows in slow[:15]:
            print(f"  {t_calc:8.2f}s  {ticker:10s}  {rows:,} rows")
    else:
        print("No ticker exceeded 1s calc time.")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
