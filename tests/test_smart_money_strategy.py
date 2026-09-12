from __future__ import annotations

from pathlib import Path

import duckdb


def test_trade_action_mapping_contract(tmp_path: Path) -> None:
    """Public SmartMoney view maps validated MarketState to BUY/HOLD/SELL deterministically."""
    connection = duckdb.connect(":memory:")
    try:
        attached_path = (tmp_path / "CherryMon-strategy.duckdb").as_posix().replace("'", "''")
        connection.execute(f"ATTACH '{attached_path}' AS CherryMon")

        schema_sql = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "DuckDB"
            / "sql"
            / "smart_money_v1_schema.sql"
        ).read_text(encoding="utf-8")
        connection.execute(schema_sql)

        connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_smart_money_ticker_score" (
                ModelId,
                Ticker,
                Date,
                SmartMoneyScore,
                ConfidenceScore,
                MarketState,
                FactorCoverage,
                DataQualityStatus,
                CalculatedAt
            )
            VALUES
                (1, 'AAA', DATE '2026-09-12', 72.0, 80.0, 'ACCUMULATION',     0.95, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-12', 80.0, 85.0, 'BREAKOUT',         0.95, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'CCC', DATE '2026-09-12', 76.0, 82.0, 'DEMAND_EXPANSION', 0.92, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'DDD', DATE '2026-09-12', 78.0, 88.0, 'SUPPLY_LOCK',       0.90, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'EEE', DATE '2026-09-12', 35.0, 86.0, 'DISTRIBUTION',      0.94, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'FFF', DATE '2026-09-12', 75.0, 85.0, 'MARKUP',            0.93, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'AAA', DATE '2026-09-11', 81.0, 58.0, 'BREAKOUT',          0.75, 'WARNING', CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-11', 25.0, 90.0, 'SELLING_CLIMAX',    0.95, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'CCC', DATE '2026-09-11', 45.0, 80.0, 'LIQUIDITY_DRYUP',   0.90, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'DDD', DATE '2026-09-11', 50.0, 80.0, 'NEUTRAL',           0.90, 'PASS',    CURRENT_TIMESTAMP)
            """
        )

        rows = connection.execute(
            """
            SELECT
                Ticker,
                Date,
                MarketState,
                DataQualityStatus,
                TradeAction
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
            ORDER BY Date DESC, Ticker
            """
        ).fetchall()

        assert rows == [
            ("AAA", rows[0][1], "ACCUMULATION", "PASS", "BUY"),
            ("BBB", rows[1][1], "BREAKOUT", "PASS", "BUY"),
            ("CCC", rows[2][1], "DEMAND_EXPANSION", "PASS", "BUY"),
            ("DDD", rows[3][1], "SUPPLY_LOCK", "PASS", "BUY"),
            ("EEE", rows[4][1], "DISTRIBUTION", "PASS", "SELL"),
            ("FFF", rows[5][1], "MARKUP", "PASS", "HOLD"),
            ("AAA", rows[6][1], "BREAKOUT", "WARNING", "HOLD"),
            ("BBB", rows[7][1], "SELLING_CLIMAX", "PASS", "HOLD"),
            ("CCC", rows[8][1], "LIQUIDITY_DRYUP", "PASS", "HOLD"),
            ("DDD", rows[9][1], "NEUTRAL", "PASS", "HOLD"),
        ]
    finally:
        connection.close()
