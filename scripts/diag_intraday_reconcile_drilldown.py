"""Drill-down for representative MATCHED mismatches (reconciliation runbook)."""
from src.Ults.DuckLib import DuckDBManager

WINDOW = (
    '(SELECT MAX("Date") - INTERVAL 30 DAY FROM "CherryMon"."main"."raw_{s}_eod")'
    ' AND (SELECT MAX("Date") FROM "CherryMon"."main"."raw_{s}_eod")'
)

QUERY = """
WITH si AS (
  SELECT "Ticker" t, "Date" d,
    FIRST("Open" ORDER BY "DateTime","RawTime","TickSeq") o,
    MAX("High") h, MIN("Low") l,
    LAST("Close" ORDER BY "DateTime","RawTime","TickSeq") c,
    SUM("Volume") v
  FROM "CherryMon"."main"."raw_{s}_intraday"
  WHERE "Date" BETWEEN {window}
  GROUP BY 1,2)
SELECT si.t ticker, si.d trade_date, si.o i_open, e."Open" e_open,
       si.h i_high, e."High" e_high, si.l i_low, e."Low" e_low,
       si.c i_close, e."Close" e_close, si.v i_vol, e."Volume" e_vol,
       (si.v - e."Volume")*1.0/NULLIF(e."Volume",0) vol_pct
FROM si JOIN "CherryMon"."main"."raw_{s}_eod" e
  ON e."Ticker" = si.t AND e."Date" = si.d
WHERE ABS(si.o - e."Open") > 0.05 OR ABS(si.h - e."High") > 0.05
   OR ABS(si.l - e."Low") > 0.05 OR ABS(si.c - e."Close") > 0.05
   OR ABS((si.v - e."Volume")*1.0/NULLIF(e."Volume",0)) > 0.01
ORDER BY ABS(si.c - e."Close") DESC NULLS LAST
LIMIT 8
"""


def main() -> None:
    manager = DuckDBManager(read_only=True)
    con = manager.get_connection(read_only=True)
    try:
        for source in ("stock", "index", "futures", "warrant"):
            sql = QUERY.format(s=source, window=WINDOW.format(s=source))
            cur = con.execute(sql)
            print(f"\n=== {source}: representative matched mismatches ===")
            print(" | ".join(d[0] for d in cur.description))
            for row in cur.fetchall():
                print(" | ".join("" if v is None else str(v) for v in row))
    finally:
        manager.close_connection(con)


if __name__ == "__main__":
    main()
