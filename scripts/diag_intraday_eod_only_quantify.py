"""Quantify EOD_ONLY cause on the latest EOD date (read-only)."""
import sys

sys.path.insert(0, ".")

from src.Ults.DuckLib import DuckDBManager

Q_TOTAL = '''
SELECT COUNT(*)
FROM "CherryMon"."main"."raw_stock_eod" e
WHERE e."Date" = (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
  AND NOT EXISTS (
      SELECT 1 FROM "CherryMon"."main"."raw_stock_intraday" i
      WHERE i."Ticker" = e."Ticker" AND i."Date" = e."Date")
'''

Q_ZERO_VOL = '''
SELECT COUNT(*)
FROM "CherryMon"."main"."raw_stock_eod" e
WHERE e."Date" = (SELECT MAX("Date") FROM "CherryMon"."main"."raw_stock_eod")
  AND e."Volume" = 0
  AND NOT EXISTS (
      SELECT 1 FROM "CherryMon"."main"."raw_stock_intraday" i
      WHERE i."Ticker" = e."Ticker" AND i."Date" = e."Date")
'''


def main() -> None:
    manager = DuckDBManager(read_only=True)
    con = manager.get_connection(read_only=True)
    try:
        total = con.execute(Q_TOTAL).fetchone()[0]
        zero_vol = con.execute(Q_ZERO_VOL).fetchone()[0]
        print(f"EOD_ONLY total on latest date: {total}")
        print(f"EOD_ONLY with Volume=0 (no-trade session): {zero_vol}")
        print(f"EOD_ONLY remaining unexplained: {total - zero_vol}")
    finally:
        manager.close_connection(con)


if __name__ == "__main__":
    main()
