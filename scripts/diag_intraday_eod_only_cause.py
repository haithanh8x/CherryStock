"""Check EOD_ONLY hypothesis: zero-volume / no-trade sessions on latest EOD date."""
import sys

sys.path.insert(0, ".")

from src.Ults.DuckLib import DuckDBManager

query_latest_intraday = """
SELECT COUNT(*), COUNT(DISTINCT "Ticker")
FROM "CherryMon"."main"."raw_stock_intraday"
WHERE "Date" = (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
"""

query_eod_zero_volume = """
SELECT COUNT(*)
FROM "CherryMon"."main"."raw_stock_eod" e
WHERE e."Date" = (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
  AND e."Volume" = 0
"""

query_eod_only_zero_vol_sample = """
SELECT e."Ticker", e."Date", e."Open", e."High", e."Low", e."Close", e."Volume"
FROM "CherryMon"."main"."raw_stock_eod" e
WHERE e."Date" = (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
  AND e."Volume" = 0
  AND NOT EXISTS (
      SELECT 1 FROM "CherryMon"."main"."raw_stock_intraday" i
      WHERE i."Ticker" = e."Ticker" AND i."Date" = e."Date"
  )
LIMIT 10
"""


def main() -> None:
    manager = DuckDBManager(read_only=True)
    con = manager.get_connection(read_only=True)
    try:
        print("stock intraday rows/tickers on latest EOD date:",
              con.execute(query_latest_intraday).fetchone())
        print("EOD rows with Volume=0 on latest date:",
              con.execute(query_eod_zero_volume).fetchone())
        print("\nSample EOD_ONLY rows (Volume=0):")
        cur = con.execute(query_eod_only_zero_vol_sample)
        print(" | ".join(d[0] for d in cur.description))
        for row in cur.fetchall():
            print(" | ".join(str(v) for v in row))
    finally:
        manager.close_connection(con)


if __name__ == "__main__":
    main()
