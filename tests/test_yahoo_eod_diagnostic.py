from __future__ import annotations

import duckdb
import pandas as pd

from cherrystock.application.services.yahoo_eod_diagnostic import (
    YahooRawOtherEodDiagnostic,
    classify_ohlc_rows,
)


class _Factory:
    def __init__(self, connection) -> None:
        self.connection = connection

    class _Reader:
        def __init__(self, connection) -> None:
            self.connection = connection

        def __enter__(self):
            return self.connection

        def __exit__(self, exc_type, exc_value, traceback):
            return None

    def reader(self):
        return self._Reader(self.connection)


def _db():
    connection = duckdb.connect()
    connection.execute("ATTACH ':memory:' AS CherryMon")
    connection.execute("CREATE SCHEMA CherryMon.main")
    connection.execute(
        """
        CREATE TABLE CherryMon.main.raw_other_eod (
            Ticker VARCHAR,
            Date DATE,
            Open DOUBLE,
            High DOUBLE,
            Low DOUBLE,
            Close DOUBLE,
            Volume BIGINT
        )
        """
    )
    return connection


def test_classify_reports_exact_rule_and_material_violation() -> None:
    frame = pd.DataFrame(
        [
            {
                "Ticker": "GC=F",
                "Date": "2026-09-22",
                "Open": 100.0,
                "High": 100.0,
                "Low": 99.0,
                "Close": 101.0,
                "Volume": 1,
            }
        ]
    )

    result = classify_ohlc_rows(frame)
    row = result.iloc[0]

    assert bool(row["InvalidOHLC"]) is True
    assert row["RuleFlags"] == "HIGH_LT_CLOSE"
    assert row["MaxViolationAbs"] == 1.0
    assert row["DiagnosticClass"] == "MATERIAL_OHLC_ENVELOPE_VIOLATION"


def test_classify_labels_tiny_violation_without_changing_exact_rule() -> None:
    frame = pd.DataFrame(
        [
            {
                "Ticker": "VND=X",
                "Date": "2026-09-22",
                "Open": 100.0,
                "High": 100.0,
                "Low": 99.0,
                "Close": 100.00000001,
                "Volume": 1,
            }
        ]
    )

    result = classify_ohlc_rows(frame, precision_tolerance_bps=0.01)
    row = result.iloc[0]

    assert bool(row["InvalidOHLC"]) is True
    assert row["RuleFlags"] == "HIGH_LT_CLOSE"
    assert row["DiagnosticClass"] == "FLOAT_PRECISION_CANDIDATE"


def test_diagnostic_uses_latest_yahoo_scope_date_and_returns_context() -> None:
    connection = _db()
    try:
        connection.execute(
            """
            INSERT INTO CherryMon.main.raw_other_eod VALUES
                ('GC=F', DATE '2026-09-19', 90, 95, 89, 94, 10),
                ('GC=F', DATE '2026-09-22', 100, 100, 99, 101, 11),
                ('VND=X', DATE '2026-09-22', 26000, 26100, 25900, 26050, 0)
            """
        )

        result = YahooRawOtherEodDiagnostic(
            connection_factory=_Factory(connection)
        ).run(context_rows=1)

        assert result["summary"]["target_date"] == "2026-09-22"
        assert result["summary"]["invalid_ohlc_count"] == 1
        assert result["invalid"].iloc[0]["Ticker"] == "GC=F"
        assert len(result["context"]) == 2
    finally:
        connection.close()


def test_diagnostic_clean_date_reports_zero_invalid() -> None:
    connection = _db()
    try:
        connection.execute(
            """
            INSERT INTO CherryMon.main.raw_other_eod VALUES
                ('BTC-USD', DATE '2026-09-22', 100, 110, 90, 105, 1000)
            """
        )

        result = YahooRawOtherEodDiagnostic(
            connection_factory=_Factory(connection)
        ).run()

        assert result["summary"]["invalid_ohlc_count"] == 0
        assert result["summary"]["material_violation_count"] == 0
        assert result["invalid"].empty
    finally:
        connection.close()
