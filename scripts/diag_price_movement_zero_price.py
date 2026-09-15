"""Diag: find tickers with zero/invalid OHLC prices that break Price Movement engine."""
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from cherrystock.config.settings import settings  # noqa: E402

con = duckdb.connect(settings.local_db_path, read_only=True)

# Zero or negative prices in OHLC source
rows = con.execute(
    """
    SELECT Ticker, COUNT(*) AS ZeroPriceRows,
           MIN(Date) AS FirstZeroDate, MAX(Date) AS LastZeroDate
    FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
    WHERE Open <= 0 OR High <= 0 OR Low <= 0 OR Close <= 0
    GROUP BY Ticker
    ORDER BY ZeroPriceRows DESC
    LIMIT 20
    """
).df()
print("Tickers with zero/negative OHLC prices:")
print(rows.to_string(index=False) if not rows.empty else "(none)")

# Open = 0 (engine start_price = 0)
df = con.execute(
    """
    SELECT Ticker, COUNT(*) AS ZeroOpenRows, MIN(Date) AS FirstZero, MAX(Date) AS LastZero
    FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
    WHERE Open = 0
    GROUP BY Ticker
    ORDER BY Ticker
    """
).df()
print("Tickers with Open = 0 (engine start_price = 0):")
print(df.to_string(index=False) if not df.empty else "(none)")

con.close()
