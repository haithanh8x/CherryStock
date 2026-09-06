"""Verify the memory-seed hypothesis: warmup + seed should converge to full run."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.smartMoneyScore import (  # noqa: E402
    calculate_base_features,
    load_benchmark_data,
    load_daily_indicator_data,
    load_market_data,
    _apply_accumulation_memory,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402

factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
con = factory.create_reader()
try:
    source_min, source_max = con.execute(
        'SELECT MIN(Date), MAX(Date) FROM "CherryMon"."main"."vw_Ticker_OHLC_D"'
    ).fetchone()
    target_date = pd.Timestamp(source_max).date()
    warmup_start = pd.Timestamp("2026-05-25")

    def build(start, seed_frame=None):
        market = load_market_data(con, tickers=None, start_date=start, end_date=source_max)
        benchmark = load_benchmark_data(con, start_date=start, end_date=source_max)
        indicators = load_daily_indicator_data(con, start_date=start, end_date=source_max)
        base = calculate_base_features(market, benchmark, indicators)
        base = base.sort_values(["Ticker", "Date"]).reset_index(drop=True)
        base["AccumulationMemoryScore"] = _apply_accumulation_memory(
            base, 0.90, seed_frame=seed_frame
        )
        return base

    full = build(pd.Timestamp(source_min))

    # Seed = persisted full-run memory at the last session before warmup (2026-05-22?).
    seed = (
        full[(full["Date"] < warmup_start) & (full["Date"] >= warmup_start - pd.Timedelta(days=10))]
        .sort_values("Date")
        .groupby("Ticker")
        .tail(1)[["Ticker", "Date", "AccumulationMemoryScore"]]
        .rename(columns={"AccumulationMemoryScore": "AccumulationMemorySeed"})
    )
    print("seed rows:", len(seed), "seed date:", seed["Date"].max())

    warm = build(warmup_start, seed_frame=seed)

    fm = full[(full["Ticker"] == "MWG") & (full["Date"] >= warmup_start)][["Date", "AccumulationMemoryScore"]].reset_index(drop=True)
    wm = warm[warm["Ticker"] == "MWG"][["Date", "AccumulationMemoryScore"]].reset_index(drop=True)
    merged = fm.merge(wm, on="Date", suffixes=("_full", "_warm"))
    merged["diff"] = merged["AccumulationMemoryScore_warm"] - merged["AccumulationMemoryScore_full"]
    print(merged.tail(3).to_string(index=False))
    print("max abs diff with seed:", merged["diff"].abs().max())
finally:
    con.close()
