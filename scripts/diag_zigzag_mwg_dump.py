"""Diag: dump all ZigZag MWG pivots + swings for review."""
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from cherrystock.config.settings import settings  # noqa: E402

con = duckdb.connect(settings.local_db_path, read_only=True)
pivots = con.execute(
    """
    SELECT PivotSeq, PivotType, PivotDate, PivotPrice, ConfirmedAtDate, ConfirmationPrice
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Pivots"
    WHERE Ticker = 'MWG'
    ORDER BY PivotSeq
    """
).df()

# Engine-level check: duplicate (date, type) pairs in a fresh calculation
con.close()

import pandas as pd  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from calcEngine.zigzag import load_mwg_source  # noqa: E402
from cherrystock.infrastructure.database.repositories.zigzag_repository import (  # noqa: E402
    ZigZagRepository,
)
from cherrystock.domain.analytics.zigzag.engine import calculate_zigzag  # noqa: E402

con = duckdb.connect(settings.local_db_path, read_only=True)
source = load_mwg_source(con)
config = ZigZagRepository(con).load_mvp_config()
calc_pivots, current, diag = calculate_zigzag(source, ticker="MWG", config=config)

keys = [(p.pivot_date, p.pivot_type) for p in calc_pivots]
dupes = {k for k in keys if keys.count(k) > 1}
print(f"calc pivots: {len(calc_pivots)}, duplicate (date,type) keys: {sorted(dupes)}")
for p in calc_pivots[:6]:
    print(p.pivot_seq, p.pivot_type, p.pivot_date, p.pivot_price, p.confirmed_at_date)
print("...")
for p in calc_pivots[-3:]:
    print(p.pivot_seq, p.pivot_type, p.pivot_date, p.pivot_price, p.confirmed_at_date)
print("current:", current)

swings = con.execute(
    """
    SELECT SwingSeq, Direction, StartDate, StartPrice, EndDate, EndPrice, ConfirmedAtDate, SwingPct
    FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
    WHERE Ticker = 'MWG'
    ORDER BY SwingSeq
    """
).df()
print("\n=== All derived swings ===")
print(swings.to_string(index=False) if not swings.empty else "(none)")

# Probe the DOWN leg state after 2014-07-21: find first Close >= 5% above candidate low
probe = con.execute(
    """
    WITH src AS (
        SELECT Date, High, Low, Close
        FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
        WHERE Ticker = 'MWG' AND Date > DATE '2014-07-21'
        ORDER BY Date
    )
    SELECT
        MIN(Date) AS FirstDateAfterPivot,
        MIN(Low) AS MinLowEarly,
        MIN(Close) FILTER (WHERE Date <= DATE '2015-12-31') AS MinClose2015
    FROM src
    """
).df()
print("\n=== Probe after 2014-07-21 ===")
print(probe.to_string(index=False))
con.close()
