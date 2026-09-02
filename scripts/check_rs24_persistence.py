"""Seq 6 persistence check: read MA50_D H20 rows from public view (read-only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.Ults.DuckLib import DuckDBManager

m = DuckDBManager(read_only=True)
c = m.get_connection()
print(c.sql("""
    SELECT "Ticker", "SourceKey", "HorizonBars", "Recommendation", "EffectivenessRunId"
    FROM "CherryMon"."main"."vw_RS_Source_Effectiveness"
    WHERE "SourceKey" = 'MA50_D' AND "HorizonBars" = 20
    ORDER BY "Ticker"
""").df())
m.close_connection()
