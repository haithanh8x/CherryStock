from __future__ import annotations

from Ults.DuckLib import DuckDBManager, exportDuckDB_metadata
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory


def test_export_duckdb_metadata_writes_indicator_csv_snapshots(
    tmp_path, monkeypatch
):
    """Export all indicator dimensions and safely replace snapshots on rerun."""

    monkeypatch.delenv("DUCKDB_ENV", raising=False)
    monkeypatch.delenv("LOCAL_DB_PATH", raising=False)

    db_path = tmp_path / "CherryMon-test.duckdb"
    output_path = tmp_path / "reference" / "DB_Metadata.md"
    factory = DuckDBConnectionFactory(db_path=db_path, duckdb_env="local")

    with factory.writer() as connection:
        connection.execute(
            """
            CREATE TABLE dim_indicator (
                IndicatorCode VARCHAR NOT NULL,
                IndicatorName VARCHAR NOT NULL,
                RequiredInputs JSON NOT NULL
            );
            CREATE TABLE dim_indicator_component (
                IndicatorCode VARCHAR NOT NULL,
                ComponentCode VARCHAR NOT NULL,
                ComponentName VARCHAR NOT NULL
            );
            CREATE TABLE dim_indicator_config (
                ConfigId BIGINT NOT NULL,
                ConfigCode VARCHAR NOT NULL,
                IndicatorCode VARCHAR NOT NULL,
                Timeframe VARCHAR NOT NULL,
                Parameters JSON NOT NULL
            );

            INSERT INTO dim_indicator VALUES
                ('RSI', 'Relative Strength Index', '["close"]');
            INSERT INTO dim_indicator_component VALUES
                ('RSI', 'VALUE', 'RSI Value');
            INSERT INTO dim_indicator_config VALUES
                (1, 'RSI14_D', 'RSI', 'Daily', '{"length": 14}');
            """
        )

    previous_factory = DuckDBManager._factory
    DuckDBManager._factory = factory
    try:
        result_path = exportDuckDB_metadata(
            db_path=db_path,
            output_path=output_path,
        )

        assert result_path == output_path
        expected_files = {
            "dim_indicator.csv",
            "dim_indicator_component.csv",
            "dim_indicator_config.csv",
        }
        assert expected_files == {
            path.name for path in output_path.parent.glob("*.csv")
        }

        with factory.reader() as connection:
            assert connection.execute(
                "SELECT IndicatorCode FROM read_csv_auto(?)",
                [str(output_path.parent / "dim_indicator.csv")],
            ).fetchall() == [("RSI",)]
            assert connection.execute(
                "SELECT ConfigCode FROM read_csv_auto(?)",
                [str(output_path.parent / "dim_indicator_config.csv")],
            ).fetchall() == [("RSI14_D",)]

        with factory.writer() as connection:
            connection.execute(
                """
                INSERT INTO dim_indicator_config VALUES
                    (2, 'RSI14_W', 'RSI', 'Weekly', '{"length": 14}')
                """
            )

        exportDuckDB_metadata(db_path=db_path, output_path=output_path)

        with factory.reader() as connection:
            assert connection.execute(
                "SELECT ConfigCode FROM read_csv_auto(?) ORDER BY ConfigId",
                [str(output_path.parent / "dim_indicator_config.csv")],
            ).fetchall() == [("RSI14_D",), ("RSI14_W",)]

        metadata = output_path.read_text(encoding="utf-8")
        assert "## AI context loading guide" in metadata
        assert "## Indicator metadata snapshots" in metadata
        assert "`dim_indicator.csv`" in metadata
        assert "`dim_indicator_component.csv`" in metadata
        assert "`dim_indicator_config.csv`" in metadata
    finally:
        DuckDBManager.close_connection()
        DuckDBManager._factory = previous_factory
