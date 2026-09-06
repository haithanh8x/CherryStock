"""Probe write capability on CherryMon.duckdb (creates and drops a temp table)."""
import duckdb

con = duckdb.connect(r"c:\onedrive\working\datafile\cherrymon.duckdb", read_only=False)
con.execute('CREATE TABLE "CherryMon"."main"."t_test_write" (i INTEGER)')
con.execute('INSERT INTO "CherryMon"."main"."t_test_write" VALUES (1)')
print(con.execute('SELECT * FROM "CherryMon"."main"."t_test_write"').fetchall())
con.execute('DROP TABLE "CherryMon"."main"."t_test_write"')
con.close()
print("write test OK")
