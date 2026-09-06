"""Inspect existing dim_smart_money_model schema (read-only)."""
import duckdb

con = duckdb.connect(r"c:\onedrive\working\datafile\cherrymon.duckdb", read_only=True)
rows = con.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE lower(table_name) = 'dim_smart_money_model' ORDER BY ordinal_position"
).fetchall()
print("dim_smart_money_model columns:")
for r in rows:
    print(r)
count = con.execute('SELECT COUNT(*) FROM "CherryMon"."main"."dim_smart_money_model"').fetchone()
print("row count:", count)
con.close()
