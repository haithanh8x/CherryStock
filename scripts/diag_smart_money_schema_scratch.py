"""Probe: run the exact schema SQL file content on a fresh in-memory DuckDB."""
import duckdb

sql = open(
    r"c:\Github\CherryStock\src\DuckDB\sql\smart_money_v1_schema.sql", encoding="utf-8"
).read()

con = duckdb.connect()  # in-memory, attach-style namespaces resolve loosely
try:
    con.execute("ATTACH ':memory:' AS CherryMon")
    con.execute("CREATE SCHEMA IF NOT EXISTS CherryMon.main")
    con.execute(sql)
    print("schema SQL executed OK on scratch DB")
except Exception as exc:
    print("ERROR:", exc)
finally:
    con.close()
