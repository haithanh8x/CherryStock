"""One-off diagnostic: find BB row with ConfigId=2 negative value (read-only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.Ults.DuckLib import DuckDBManager

m = DuckDBManager(read_only=True)
c = m.get_connection()
print(c.sql("""
    SELECT v."Ticker", v."Date", v."ConfigId", v."ComponentCode", v."Value",
           cfg."ConfigCode", cfg."IndicatorCode", cfg."Timeframe"
    FROM "CherryMon"."main"."vw_Ticker_indicators" v
    INNER JOIN "CherryMon"."main"."vw_Indicator_config" cfg
        ON cfg."ConfigId" = v."ConfigId" AND cfg."ComponentCode" = v."ComponentCode"
    WHERE v."ConfigId" = 2
      AND v."Value" <= 0
    ORDER BY v."Date" DESC
    LIMIT 10
""").df())
print(c.sql("""
    SELECT "ConfigId", "ConfigCode", "IndicatorCode", "Timeframe", "ComponentCode"
    FROM "CherryMon"."main"."vw_Indicator_config"
    WHERE "ConfigId" = 2
""").df())
m.close_connection()
