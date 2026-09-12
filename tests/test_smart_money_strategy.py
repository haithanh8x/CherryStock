from __future__ import annotations

from pathlib import Path

import duckdb
import pytest


def test_trade_action_mapping_contract(tmp_path: Path) -> None:
    """Public SmartMoney view maps action and action confidence deterministically."""
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
                (1, 'AAA', DATE '2026-09-12', 72.0, 80.0,   'ACCUMULATION',     0.95, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-12', 80.0, 85.0,   'BREAKOUT',         0.95, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'CCC', DATE '2026-09-12', 76.0, 82.0,   'DEMAND_EXPANSION', 0.92, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'DDD', DATE '2026-09-12', 78.0, 88.0,   'SUPPLY_LOCK',       0.90, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'EEE', DATE '2026-09-12', 35.0, 86.135, 'DISTRIBUTION',      0.94, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'FFF', DATE '2026-09-12', 75.0, 85.0,   'MARKUP',            0.93, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'AAA', DATE '2026-09-11', 81.0, 58.0,   'BREAKOUT',          0.75, 'WARNING', CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-11', 25.0, 90.0,   'SELLING_CLIMAX',    0.95, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'CCC', DATE '2026-09-11', 45.0, 80.0,   'LIQUIDITY_DRYUP',   0.90, 'PASS',    CURRENT_TIMESTAMP),
                (1, 'DDD', DATE '2026-09-11', 50.0, 97.135, 'NEUTRAL',           0.90, 'PASS',    CURRENT_TIMESTAMP)
            """
        )

        connection.execute(
            """
            INSERT INTO "CherryMon"."main"."cal_smart_money_factor_values" (
                ModelId,
                Ticker,
                Date,
                FactorId,
                RawValue,
                NormalizedValue,
                DataQuality,
                SourceCode,
                CalculatedAt
            )
            VALUES
                -- ACCUMULATION: min(80, 70) => state strength 70
                (1, 'AAA', DATE '2026-09-12', 5,  NULL, 80.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'AAA', DATE '2026-09-12', 6,  NULL, 70.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),

                -- BREAKOUT: min(90, 88, 80) => state strength 80
                (1, 'BBB', DATE '2026-09-12', 1,  NULL, 90.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-12', 2,  NULL, 88.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-12', 4,  NULL, 80.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),

                -- DEMAND_EXPANSION: min(88, 78, 70) => state strength 70
                (1, 'CCC', DATE '2026-09-12', 2,  NULL, 88.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'CCC', DATE '2026-09-12', 3,  NULL, 78.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'CCC', DATE '2026-09-12', 4,  NULL, 70.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),

                -- SUPPLY_LOCK: min(90, 75) => state strength 75
                (1, 'DDD', DATE '2026-09-12', 7,  NULL, 90.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'DDD', DATE '2026-09-12', 6,  NULL, 75.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),

                -- DISTRIBUTION: state strength 92; final confidence is capped by upstream 86.135
                (1, 'EEE', DATE '2026-09-12', 10, NULL, 92.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),

                -- MARKUP: min(80, 75) => state strength 75
                (1, 'FFF', DATE '2026-09-12', 9,  NULL, 80.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'FFF', DATE '2026-09-12', 4,  NULL, 75.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),

                -- SELLING_CLIMAX: min(80, 90) => state strength 80
                (1, 'BBB', DATE '2026-09-11', 10, NULL, 80.0, 'PASS', 'TEST', CURRENT_TIMESTAMP),
                (1, 'BBB', DATE '2026-09-11', 2,  NULL, 90.0, 'PASS', 'TEST', CURRENT_TIMESTAMP)
            """
        )

        rows = connection.execute(
            """
            SELECT
                Ticker,
                Date,
                MarketState,
                DataQualityStatus,
                TradeAction,
                TradeActionConfidenceScore
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
            ORDER BY Date DESC, Ticker
            """
        ).fetchall()

        expected = [
            ("AAA", "ACCUMULATION", "PASS", "BUY", 76.0),
            ("BBB", "BREAKOUT", "PASS", "BUY", 83.0),
            ("CCC", "DEMAND_EXPANSION", "PASS", "BUY", 77.2),
            ("DDD", "SUPPLY_LOCK", "PASS", "BUY", 82.8),
            ("EEE", "DISTRIBUTION", "PASS", "SELL", 86.135),
            ("FFF", "MARKUP", "PASS", "HOLD", 81.0),
            ("AAA", "BREAKOUT", "WARNING", "HOLD", 0.0),
            ("BBB", "SELLING_CLIMAX", "PASS", "HOLD", 86.0),
            ("CCC", "LIQUIDITY_DRYUP", "PASS", "HOLD", 80.0),
            ("DDD", "NEUTRAL", "PASS", "HOLD", 97.135),
        ]

        assert len(rows) == len(expected)
        for row, expected_row in zip(rows, expected, strict=True):
            ticker, _date, state, quality, action, action_confidence = row
            exp_ticker, exp_state, exp_quality, exp_action, exp_confidence = expected_row
            assert (ticker, state, quality, action) == (
                exp_ticker,
                exp_state,
                exp_quality,
                exp_action,
            )
            assert action_confidence == pytest.approx(exp_confidence, abs=1e-9)
            assert 0.0 <= action_confidence <= 100.0
            assert action_confidence <= row_confidence(connection, ticker, _date) + 1e-9
    finally:
        connection.close()


def row_confidence(connection: duckdb.DuckDBPyConnection, ticker: str, trade_date) -> float:
    return float(
        connection.execute(
            """
            SELECT ConfidenceScore
            FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
            WHERE Ticker = ? AND Date = ?
            """,
            [ticker, trade_date],
        ).fetchone()[0]
    )
