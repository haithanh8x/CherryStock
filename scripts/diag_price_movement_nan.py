"""Diag: find tickers producing NaN/non-finite Persistence metrics in Price Movement fast path."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.repositories.price_movement_repository import (  # noqa: E402
    PriceMovementRepository,
)
from cherrystock.domain.analytics.price_movement.runtime import (  # noqa: E402
    calculate_ticker_movement_fast,
)

con = duckdb.connect(settings.local_db_path, read_only=True)
config = PriceMovementRepository(con).load_enabled_config()
print("Config:", config.config_id, config.model_code, config.model_version)
frame = con.execute(
    """
    SELECT * FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
    """
).df()
con.close()

tickers = frame["Ticker"].unique().tolist()
bad = []
for ticker in sorted(tickers):
    tf = frame[frame["Ticker"] == ticker]
    events, daily = calculate_ticker_movement_fast(tf, ticker=ticker, config=config)
    for row in daily:
        for col in ("PersistencePercentile", "PersistenceScore", "MagnitudePercentile", "VelocityPercentile"):
            val = row.get(col)
            if val is not None and not pd.notna(val):
                bad.append((ticker, str(row.get("Date")), col, repr(val)))
            elif val is not None and isinstance(val, float) and abs(val) > 100.0:
                bad.append((ticker, str(row.get("Date")), col, repr(val)))
    for ev in events:
        for col in ("persistence_percentile", "magnitude_percentile", "velocity_percentile"):
            val = getattr(ev, col, None)
            if val is not None and not pd.notna(val):
                bad.append((ticker, str(ev.confirmed_at_date), col, repr(val)))

print(f"Bad rows: {len(bad)}")
for item in bad[:30]:
    print(item)
