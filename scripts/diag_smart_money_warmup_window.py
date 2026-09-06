"""Diagnose incremental-vs-full convergence drift for SmartMoneyScore (read-only)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.smartMoneyScore import (  # noqa: E402
    load_daily_indicator_data,
    load_market_data,
    resolve_warmup_start,
)
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402

factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
con = factory.create_reader()
try:
    source_min, source_max = con.execute(
        'SELECT MIN(Date), MAX(Date) FROM "CherryMon"."main"."vw_Ticker_OHLC_D"'
    ).fetchone()
    print("source bounds:", source_min, source_max)

    target_start = pd.Timestamp(source_max).date() - pd.Timedelta(days=1)
    warmup_start = resolve_warmup_start(
        con, target_start=pd.Timestamp(target_start), source_min=pd.Timestamp(source_min), sessions=70
    )
    print("target_start:", target_start, "warmup_start:", warmup_start)

    # Indicator availability inside the warmup window vs persisted scores.
    ind = load_daily_indicator_data(con, start_date=warmup_start, end_date=source_max)
    print("indicator rows in warmup:", len(ind))
    print("indicator min/max date:", ind["Date"].min(), ind["Date"].max())
    print("indicator OBV non-null:", int(ind["OBV"].notna().sum()),
          "AD non-null:", int(ind["AD"].notna().sum()))

    market = load_market_data(con, tickers=None, start_date=warmup_start, end_date=source_max)
    mw = market[market["Ticker"] == "MWG"]
    print("MWG market rows in warmup:", len(mw))
finally:
    con.close()
