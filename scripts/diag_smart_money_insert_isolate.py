"""Isolate the failing INSERT statement for dim_smart_money_model."""
import duckdb

con = duckdb.connect()
con.execute("ATTACH ':memory:' AS CherryMon")
con.execute("CREATE SCHEMA IF NOT EXISTS CherryMon.main")

con.execute(
    """
    CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_smart_money_model" (
        ModelId BIGINT NOT NULL,
        ModelCode VARCHAR NOT NULL,
        ModelVersion VARCHAR NOT NULL,
        Description VARCHAR,
        IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
        EffectiveFrom DATE NOT NULL DEFAULT DATE '2000-01-01',
        EffectiveTo DATE,
        CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (ModelId),
        UNIQUE (ModelCode, ModelVersion)
    )
    """
)

insert_sql = """
INSERT INTO "CherryMon"."main"."dim_smart_money_model" (
    ModelId, ModelCode, ModelVersion, Description, IsEnabled,
    EffectiveFrom, EffectiveTo, UpdatedAt
)
VALUES (
    1,
    'SMART_MONEY_V1',
    '1.0.0',
    'State-aware SmartMoneyScore V1.',
    TRUE,
    DATE '2000-01-01',
    NULL,
    CURRENT_TIMESTAMP
)
ON CONFLICT (ModelId) DO UPDATE SET
    ModelCode = EXCLUDED.ModelCode,
    ModelVersion = EXCLUDED.ModelVersion,
    Description = EXCLUDED.Description,
    IsEnabled = EXCLUDED.IsEnabled,
    EffectiveFrom = EXCLUDED.EffectiveFrom,
    EffectiveTo = EXCLUDED.EffectiveTo,
    UpdatedAt = now()
"""
try:
    con.execute(insert_sql)
    print("isolated insert OK:", con.execute("SELECT ModelId, ModelCode FROM CherryMon.main.dim_smart_money_model").fetchall())
except Exception as exc:
    print("ISOLATED ERROR:", exc)

con.close()
