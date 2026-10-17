"""Focused tests for AmiBroker APX full-history indicator replacement."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from scripts.sync_amibroker_indicator_full import (
    EXPECTED_COLUMNS,
    SPECS,
    prepare_stage,
    replace_full_history,
    validate_apx,
)


def _csv(path: Path, *, tickers=("AAA", "BBB"), dates=("2025-01-02", "2025-01-03")) -> Path:
    names = ["Ticker", "Date", *(s.csv_column for s in SPECS)]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for ticker in tickers:
            for day in dates:
                row = {"Ticker": ticker, "Date": day}
                for s in SPECS:
                    row[s.csv_column] = "1.5"
                writer.writerow(row)
    return path


def _database() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("ATTACH ':memory:' AS CherryMon")
    con.execute(
        """
        CREATE TABLE CherryMon.main.dim_indicator (
            IndicatorCode VARCHAR PRIMARY KEY,
            IndicatorName VARCHAR NOT NULL,
            Category VARCHAR NOT NULL,
            Engine VARCHAR NOT NULL,
            FunctionName VARCHAR NOT NULL,
            RequiredInputs JSON NOT NULL,
            ParameterSchema JSON,
            Description VARCHAR,
            IsActive BOOLEAN NOT NULL DEFAULT TRUE,
            CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt TIMESTAMP
        );
        CREATE TABLE CherryMon.main.dim_indicator_component (
            IndicatorCode VARCHAR,
            ComponentCode VARCHAR,
            ComponentName VARCHAR,
            OutputPrefix VARCHAR,
            SortOrder INTEGER,
            ValueSemantic VARCHAR,
            Unit VARCHAR,
            IsPrimary BOOLEAN NOT NULL DEFAULT FALSE,
            IsActive BOOLEAN NOT NULL DEFAULT TRUE,
            PRIMARY KEY(IndicatorCode, ComponentCode)
        );
        CREATE SEQUENCE CherryMon.main.seq_indicator_config START 1;
        CREATE TABLE CherryMon.main.dim_indicator_config (
            ConfigId BIGINT PRIMARY KEY DEFAULT nextval('CherryMon.main.seq_indicator_config'),
            ConfigCode VARCHAR UNIQUE NOT NULL,
            IndicatorCode VARCHAR NOT NULL,
            Timeframe VARCHAR NOT NULL,
            Parameters JSON NOT NULL,
            WarmupBars INTEGER,
            IsEnabled BOOLEAN NOT NULL DEFAULT TRUE,
            Description VARCHAR,
            CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UpdatedAt TIMESTAMP
        );
        CREATE TABLE CherryMon.main.cal_indicator_values (
            Ticker VARCHAR NOT NULL,
            Date DATE NOT NULL,
            ConfigId BIGINT NOT NULL,
            ComponentCode VARCHAR NOT NULL,
            Value DOUBLE,
            CalculatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (Ticker, Date, ConfigId, ComponentCode)
        );
        CREATE VIEW CherryMon.main.vw_Ticker_indicators AS
            SELECT v.Ticker, v.Date, v.ConfigId, v.ComponentCode,
                   v.Value, c.IndicatorCode, c.Timeframe, c.WarmupBars
            FROM CherryMon.main.cal_indicator_values v
            JOIN CherryMon.main.dim_indicator_config c ON c.ConfigId = v.ConfigId;
        """
    )
    return con


def test_expected_dwm_column_contract() -> None:
    assert len(SPECS) == 108
    assert len(EXPECTED_COLUMNS) == 108
    assert {"MA20_D", "MA20_W", "MA20_M", "BB20_2_LOWER_D",
            "ADX14_PLUS_DI_W", "STOCH14_3_3_K_M", "VWAP20_M"} <= EXPECTED_COLUMNS


def test_apx_enforces_all_quotes_daily_and_all_symbols(tmp_path: Path) -> None:
    afl = tmp_path / "Export_Indicator.afl"
    afl.write_text("Filter=1;", encoding="utf-8")
    apx = afl.with_suffix(".apx")
    apx.write_text(
        "<AmiBroker-Analysis><General>"
        "<RangeType>0</RangeType><ApplyTo>0</ApplyTo>"
        f"<FormulaPath>{afl}</FormulaPath>"
        "<FormulaContent>CS_ExportIndicators();</FormulaContent>"
        "</General><BacktestSettings><Periodicity>0</Periodicity>"
        "</BacktestSettings></AmiBroker-Analysis>",
        encoding="utf-8",
    )
    validate_apx(apx, afl)
    apx.write_text(apx.read_text().replace("<RangeType>0", "<RangeType>1"), encoding="utf-8")
    with pytest.raises(ValueError, match="All quotations"):
        validate_apx(apx, afl)


def test_stage_and_atomic_replacement_are_idempotent(tmp_path: Path) -> None:
    con = _database()
    try:
        path = _csv(tmp_path / "indicator.csv")
        summary = prepare_stage(con, path, min_dates=2, min_tickers=2)
        assert summary["tickers"] == 2
        assert summary["distinct_dates"] == 2
        outcome = replace_full_history(con, summary)
        assert outcome["inserted"] == summary["rows"]
        assert outcome["public_view_rows"] == summary["rows"]
        ids = dict(con.execute(
            "SELECT ConfigCode, ConfigId FROM CherryMon.main.dim_indicator_config"
        ).fetchall())
        assert set(("MA20_D", "ATR14_W", "OBV_M")) <= set(ids)

        # A new CSV staging run replaces everything; config identities stay stable.
        con.execute("DROP TABLE _afl_stage")
        con.execute("DROP TABLE _afl_unpivot")
        con.execute("DROP TABLE _afl_map")
        con.execute("DROP TABLE _afl_csv")
        again = prepare_stage(con, path, min_dates=2, min_tickers=2)
        replace_full_history(con, again)
        assert dict(con.execute(
            "SELECT ConfigCode, ConfigId FROM CherryMon.main.dim_indicator_config"
        ).fetchall()) == ids
        assert con.execute(
            "SELECT COUNT(*) FROM CherryMon.main.cal_indicator_values"
        ).fetchone()[0] == summary["rows"]
    finally:
        con.close()


def test_view_mismatch_rolls_back_old_data(tmp_path: Path) -> None:
    con = _database()
    try:
        con.execute(
            "INSERT INTO CherryMon.main.cal_indicator_values "
            "(Ticker, Date, ConfigId, ComponentCode, Value) "
            "VALUES ('OLD', DATE '2025-01-02', 999, 'VALUE', 123)"
        )
        con.execute("DROP VIEW CherryMon.main.vw_Ticker_indicators")
        con.execute(
            "CREATE VIEW CherryMon.main.vw_Ticker_indicators AS "
            "SELECT v.Ticker, v.Date, v.ConfigId, v.ComponentCode, "
            "v.Value, c.IndicatorCode, c.Timeframe, c.WarmupBars "
            "FROM CherryMon.main.cal_indicator_values v "
            "JOIN CherryMon.main.dim_indicator_config c ON c.ConfigId=v.ConfigId "
            "WHERE v.Ticker = 'NOPE'"
        )
        summary = prepare_stage(con, _csv(tmp_path / "indicator.csv"), min_dates=2, min_tickers=2)
        with pytest.raises(RuntimeError, match="Public view loses rows"):
            replace_full_history(con, summary)
        assert con.execute(
            "SELECT Ticker, Value FROM CherryMon.main.cal_indicator_values"
        ).fetchall() == [("OLD", 123.0)]
        assert con.execute(
            "SELECT COUNT(*) FROM CherryMon.main.dim_indicator_config"
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_partial_export_is_rejected_without_deletion(tmp_path: Path) -> None:
    con = _database()
    try:
        path = _csv(tmp_path / "partial.csv")
        rows = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(rows[:2]) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="incomplete"):
            prepare_stage(con, path, min_dates=2, min_tickers=2)
    finally:
        con.close()
