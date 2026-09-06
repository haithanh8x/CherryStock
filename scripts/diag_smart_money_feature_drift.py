"""Compare full-run factor inputs vs incremental-warmup inputs for MWG (read-only)."""
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

    def features(start):
        market = load_market_data(con, tickers=None, start_date=start, end_date=source_max)
        benchmark = load_benchmark_data(con, start_date=start, end_date=source_max)
        indicators = load_daily_indicator_data(con, start_date=start, end_date=source_max)
        base = calculate_base_features(market, benchmark, indicators)
        return base[(base["Ticker"] == "MWG") & (base["Date"] == pd.Timestamp(target_date))]

    full = features(pd.Timestamp(source_min))
    warm = features(pd.Timestamp("2026-05-25"))

    cols = [
        "AccumulationScore", "OBVSlope20", "ADSlope20", "CLV20", "RS20",
        "RelativeStrengthScore", "TrendScore", "FreshFlowScore",
        "RelativeLiquidityScore", "LiquidityAccelerationScore",
        "DistributionScore", "LiquidityCompressionScore", "CloseStrengthScore",
    ]
    print(f"{'feature':<28} full-run      warmup-run")
    for c in cols:
        f = full[c].iloc[0] if not full.empty else float("nan")
        w = warm[c].iloc[0] if not warm.empty else float("nan")
        diff = "" if pd.isna(f) and pd.isna(w) else f"{(w - f):+.4f}"
        print(f"{c:<28} {f:>10.4f}   {w:>10.4f}  {diff}")
finally:
    con.close()
