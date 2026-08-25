from datetime import date, timedelta

import duckdb
import pytest

from src.Ults.DataValidation import validate_data_quality


def _create_price_table(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE raw_stock_eod (
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


def _insert_price_history(
    connection: duckdb.DuckDBPyConnection,
    end_date: date,
    periods: int = 21,
    symbols: tuple[str, ...] = ("AAA", "BBB", "CCC"),
) -> None:
    rows = []
    for day_offset in range(periods):
        trading_date = end_date - timedelta(days=(periods - 1 - day_offset))
        for symbol in symbols:
            rows.append((symbol, trading_date, 10.0, 12.0, 9.0, 11.0, 1000))
    connection.executemany(
        "INSERT INTO raw_stock_eod VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def test_validate_data_quality_happy_path() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
        required_cols=["Ticker", "Date", "Close", "Volume"],
    )

    assert result["status"] == "PASS"
    assert result["metrics"]["max_date"] == "2026-08-21"
    assert result["metrics"]["row_count_current"] == 3
    assert result["metrics"]["symbol_count_current"] == 3
    assert result["metrics"]["duplicate_count"] == 0


def test_validate_data_quality_stale_data_fails() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 20)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=date(2026, 8, 21),
    )

    assert result["status"] == "FAIL"
    assert result["metrics"]["date_lag"] == 1
    assert any("stale" in message.lower() for message in result["errors"])


def test_validate_data_quality_detects_symbol_drop() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(
        connection,
        current_date - timedelta(days=1),
        symbols=("AAA", "BBB", "CCC", "DDD", "EEE", "FFF"),
    )
    connection.executemany(
        "INSERT INTO raw_stock_eod VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("AAA", current_date, 10.0, 12.0, 9.0, 11.0, 1000),
            ("BBB", current_date, 10.0, 12.0, 9.0, 11.0, 1000),
        ],
    )

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
        max_symbol_change_pct=0.20,
        max_row_change_pct=0.20,
    )

    assert result["status"] == "FAIL"
    assert result["metrics"]["missing_symbol_count"] == 4
    assert set(result["metrics"]["missing_symbols"]) == {"CCC", "DDD", "EEE", "FFF"}


def test_validate_data_quality_duplicate_key_fails() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)
    connection.execute(
        "INSERT INTO raw_stock_eod VALUES ('AAA', ?, 10, 12, 9, 11, 1000)",
        [current_date],
    )

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
    )

    assert result["status"] == "FAIL"
    assert result["metrics"]["duplicate_count"] == 1


def test_validate_data_quality_required_null_fails() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)
    connection.execute(
        "UPDATE raw_stock_eod SET Close = NULL WHERE Ticker = 'AAA' AND Date = ?",
        [current_date],
    )

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
        required_cols=["Ticker", "Date", "Close"],
        max_null_rate=0.01,
    )

    assert result["status"] == "FAIL"
    assert result["metrics"]["null_rate"]["Close"] == pytest.approx(1 / 3)


def test_validate_data_quality_single_period_warns_without_crashing() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    connection.execute(
        "INSERT INTO raw_stock_eod VALUES ('AAA', ?, 10, 12, 9, 11, 1000)",
        [current_date],
    )

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
    )

    assert result["status"] == "WARNING"
    assert result["metrics"]["row_count_previous"] is None
    assert result["metrics"]["symbol_count_previous"] is None


def test_validate_data_quality_is_deterministic() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)

    first = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
    )
    second = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
    )

    assert first == second
    assert connection.execute("SELECT COUNT(*) FROM raw_stock_eod").fetchone()[0] == 63


def test_validate_data_quality_missing_table_returns_fail() -> None:
    connection = duckdb.connect(":memory:")

    result = validate_data_quality(
        connection=connection,
        table_name="missing_table",
        expected_date=date(2026, 8, 21),
    )

    assert result["status"] == "FAIL"
    assert any("does not exist" in message for message in result["errors"])


def test_validate_data_quality_invalid_config_raises() -> None:
    connection = duckdb.connect(":memory:")

    with pytest.raises(ValueError, match="history_window"):
        validate_data_quality(
            connection=connection,
            table_name="raw_stock_eod",
            expected_date=date(2026, 8, 21),
            history_window=1,
        )


def test_validate_data_quality_supports_fa_snapshot_without_ohlc() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    connection.execute(
        """
        CREATE TABLE raw_stock_fa (
            Ticker VARCHAR,
            Date DATE,
            PE DOUBLE,
            EPS DOUBLE
        )
        """
    )
    connection.executemany(
        "INSERT INTO raw_stock_fa VALUES (?, ?, ?, ?)",
        [
            ("AAA", current_date, 12.0, 2.5),
            ("BBB", current_date, 15.0, 1.8),
            ("CCC", current_date, 10.0, 3.1),
        ],
    )

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_fa",
        expected_date=current_date,
        key_cols=["Ticker"],
        required_cols=["Ticker", "Date"],
    )

    assert result["status"] == "WARNING"
    assert result["errors"] == []
    assert result["metrics"]["invalid_ohlc_count"] == 0
    assert result["metrics"]["duplicate_count"] == 0


def test_validate_data_quality_optional_cols_pass_within_threshold() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)
    connection.execute("ALTER TABLE raw_stock_eod ADD COLUMN MA20_W DOUBLE")
    # 1/3 rows NULL = 33% > max_null_rate mặc định nhưng < max_optional_null_rate
    connection.execute(
        "UPDATE raw_stock_eod SET MA20_W = 11.0 WHERE Ticker IN ('AAA', 'BBB')"
    )

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
        required_cols=["Ticker", "Date", "Close"],
        optional_null_rate_cols=["MA20_W"],
        max_optional_null_rate=0.35,
    )

    assert result["status"] == "PASS"
    assert result["metrics"]["null_rate"]["MA20_W"] == pytest.approx(1 / 3)


def test_validate_data_quality_optional_col_exceeding_threshold_fails() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)
    connection.execute("ALTER TABLE raw_stock_eod ADD COLUMN MA20_M DOUBLE")
    # Tất cả NULL = 100% > ngưỡng 35%
    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
        required_cols=["Ticker", "Date", "Close"],
        optional_null_rate_cols=["MA20_M"],
        max_optional_null_rate=0.35,
    )

    assert result["status"] == "FAIL"
    assert any(
        "MA20_M NULL rate" in error and "max_optional_null_rate" in error
        for error in result["errors"]
    )


def test_validate_data_quality_missing_optional_column_warns_not_fails() -> None:
    connection = duckdb.connect(":memory:")
    current_date = date(2026, 8, 21)
    _create_price_table(connection)
    _insert_price_history(connection, current_date)

    result = validate_data_quality(
        connection=connection,
        table_name="raw_stock_eod",
        expected_date=current_date,
        required_cols=["Ticker", "Date", "Close"],
        optional_null_rate_cols=["MA50_M"],
    )

    assert result["status"] == "WARNING"
    assert any("MA50_M" in warning for warning in result["warnings"])
