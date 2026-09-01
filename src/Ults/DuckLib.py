import os
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from Ults.Timing import timeit, toggle_print
from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory


_INDICATOR_METADATA_EXPORTS: tuple[tuple[str, str], ...] = (
    ("dim_indicator", "dim_indicator.parquet"),
    ("dim_indicator_component", "dim_indicator_component.parquet"),
    ("dim_indicator_config", "dim_indicator_config.parquet"),
)


def _quote_identifier(value: str) -> str:
    """Return a safely quoted DuckDB identifier."""
    return '"' + value.replace('"', '""') + '"'


def _quote_sql_literal(value: str) -> str:
    """Return a safely quoted DuckDB string literal."""
    return "'" + value.replace("'", "''") + "'"


class DuckDBManager:
    """Compatibility facade around connection factory based DuckDB access."""

    _factory: DuckDBConnectionFactory | None = None
    _opened_connections: list[duckdb.DuckDBPyConnection] = []

    def __init__(self, read_only: bool = False) -> None:
        self._read_only = read_only
        self._connection: duckdb.DuckDBPyConnection | None = None

    @classmethod
    def _get_factory(cls) -> DuckDBConnectionFactory:
        if cls._factory is None:
            cls._factory = DuckDBConnectionFactory(
                db_path=settings.local_db_path,
                duckdb_env=settings.duckdb_env,
                motherduck_token=settings.motherduck_token,
            )
        return cls._factory

    @classmethod
    def _create_connection(cls, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Create a fresh connection from the centralized factory."""
        factory = cls._get_factory()
        return factory.create_reader() if read_only else factory.create_writer()

    @classmethod
    def get_connection(cls, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Return a fresh connection and track it for optional compatibility close call."""
        connection = cls._create_connection(read_only)
        cls._opened_connections.append(connection)
        return connection

    @classmethod
    def close_connection(cls, connection: duckdb.DuckDBPyConnection | None = None) -> None:
        """Close one connection (preferred) or all tracked compatibility connections."""
        if connection is not None:
            try:
                if not getattr(connection, "closed", False):
                    connection.close()
            except Exception:
                pass

            cls._opened_connections = [
                conn for conn in cls._opened_connections if conn is not connection
            ]
            return

        for conn in cls._opened_connections:
            try:
                if not getattr(conn, "closed", False):
                    conn.close()
            except Exception:
                pass
        cls._opened_connections = []

    def __enter__(self):
        self._connection = self.get_connection(read_only=self._read_only)
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._connection is not None:
            self.close_connection(self._connection)
            self._connection = None
        return False


@timeit
@toggle_print(allow_print=False)
def executeDuckSQL(
    con: duckdb.DuckDBPyConnection,
    sql_file_path: str,
    sql_description: str | None = None,
) -> None:
    """Execute a SQL script file on the supplied DuckDB connection.

    ``sql_description`` is optional and exists so orchestration/UI callers can
    attach a human-readable step name without changing legacy call sites.
    """
    if not os.path.exists(sql_file_path):
        raise FileNotFoundError(f"Không tìm thấy file SQL tại đường dẫn: {sql_file_path}")

    description = sql_description or Path(sql_file_path).name

    try:
        with open(sql_file_path, "r", encoding="utf-8") as file:
            sql_script = file.read()
        print(f"Đang thực thi SQL: {description} | file: {sql_file_path}...")
        con.execute(sql_script)
        print(f"Cập nhật dữ liệu thành công: {description}")
    except Exception as e:
        print(f"Có lỗi xảy ra khi thực thi {description}: {e}")
        raise


def returnSQL(con: duckdb.DuckDBPyConnection, sqlString: str):
    """
    Thực thi câu lệnh SELECT trên kết nối DuckDB và trả về kết quả dưới dạng Pandas DataFrame.

    :param con: Đối tượng kết nối DuckDB (duckdb Connection)
    :param sqlString: Chuỗi câu lệnh SQL SELECT cần truy vấn (str)
    :return: Pandas DataFrame chứa kết quả truy vấn, hoặc None nếu xảy ra lỗi.
    """
    clean_sql = sqlString.strip().lower()

    if not (clean_sql.startswith("select") or clean_sql.startswith("with")):
        print("⚠️ [Cảnh báo]: Hàm này chỉ hỗ trợ các câu lệnh truy vấn dữ liệu (SELECT / WITH).")
        return None

    try:
        df_result = con.execute(sqlString).df()
        return df_result
    except Exception as e:
        print(f"[Lỗi thực thi SQL trong returnSQL]: {e}")
        return None


def exportDuckDB_metadata(
    db_path: str | os.PathLike[str] | None = None,
    output_path: str | os.PathLike[str] | None = None,
) -> Path:
    """Export schema documentation and indicator dimension snapshots.

    The default output set is written to ``docs/reference`` and contains
    ``DB_Metadata.md`` plus one Parquet file for each indicator dimension.
    A custom ``output_path`` changes the Markdown path and places the Parquet
    snapshots in that file\'s parent directory.
    """
    source_db = Path(db_path).expanduser() if db_path else settings.local_db_path.expanduser()
    target_path = (
        Path(output_path).expanduser()
        if output_path
        else (settings.project_root / "docs" / "reference" / "DB_Metadata.md").expanduser()
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if not source_db.exists():
        raise FileNotFoundError(f"Không tìm thấy file DuckDB tại: {source_db}")

    sections: list[str] = []
    sections.append("# DuckDB Metadata")
    sections.append("")
    sections.append(f"- Generated at: {datetime.now(timezone.utc).isoformat()}")
    sections.append(f"- Database file: `{source_db}`")
    sections.append(f"- Output file: `{target_path}`")
    sections.append("")
    sections.append("## AI context loading guide")
    sections.append("")
    sections.append("Use this generated reference set in the following order:")
    sections.append("")
    sections.append("1. Read `DB_Metadata.md` for database objects, columns, types, nullability and defaults.")
    sections.append("2. Read `dim_indicator.parquet` for indicator master definitions and runtime/library mappings.")
    sections.append("3. Read `dim_indicator_component.parquet` for multi-output component contracts.")
    sections.append("4. Read `dim_indicator_config.parquet` for executable parameter/timeframe configurations.")
    sections.append("5. Join the three snapshots by `IndicatorCode`; use `ConfigId` for calculated-value relationships and `ComponentCode` for component relationships.")
    sections.append("")
    sections.append("The Parquet files are data snapshots generated from the same DuckDB export run. Do not infer current configuration values from the Markdown schema alone.")
    sections.append("")

    try:
        with DuckDBManager(read_only=True) as con:
            table_relation = con.sql(
                """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name
                """
            )
            table_df = table_relation.df()
            table_rows = table_df.itertuples(index=False, name=None)

            sections.append(f"- Schema count: {len({row[0] for row in table_rows})}")
            sections.append(f"- Table/view count: {len(table_df)}")
            sections.append("")
            sections.append("## Schemas")
            sections.append("")
            for schema_name in sorted(
                {
                    row[0]
                    for row in table_df[["table_schema"]].itertuples(
                        index=False, name=None
                    )
                }
            ):
                sections.append(f"- `{schema_name}`")
            sections.append("")
            sections.append("## Tables")
            sections.append("")
            for schema_name, table_name, table_type in table_df[
                ["table_schema", "table_name", "table_type"]
            ].itertuples(index=False, name=None):
                if table_type.lower() in {"base table", "view"}:
                    sections.append(f"- `{schema_name}`.`{table_name}` ({table_type})")
            sections.append("")
            sections.append("## Objects")
            sections.append("")

            for schema_name, table_name, table_type in table_df[
                ["table_schema", "table_name", "table_type"]
            ].itertuples(index=False, name=None):
                column_relation = con.sql(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = ? AND table_name = ?
                    ORDER BY ordinal_position
                    """,
                    params=[schema_name, table_name],
                )
                column_df = column_relation.df()

                sections.append(f"### {schema_name}.{table_name} ({table_type})")
                sections.append("")
                sections.append("| Column | Type | Nullable | Default |")
                sections.append("| --- | --- | --- | --- |")
                for row in column_df.itertuples(index=False, name=None):
                    column_name, data_type, is_nullable, column_default = row
                    default_value = column_default if column_default is not None else ""
                    sections.append(
                        f"| `{column_name}` | `{data_type}` | `{is_nullable}` | `{default_value}` |"
                    )
                sections.append("")

            sections.append("## Indicator metadata snapshots")
            sections.append("")
            sections.append("| DuckDB source | Parquet file | Rows |")
            sections.append("| --- | --- | ---: |")

            for table_name, file_name in _INDICATOR_METADATA_EXPORTS:
                column_rows = con.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'main' AND table_name = ?
                    ORDER BY ordinal_position
                    """,
                    [table_name],
                ).fetchall()
                if not column_rows:
                    raise RuntimeError(
                        f"Không tìm thấy bảng CherryMon.main.{table_name} để export."
                    )

                column_list = ", ".join(
                    _quote_identifier(column_name) for (column_name,) in column_rows
                )
                qualified_table = (
                    f'{_quote_identifier("main")}.{_quote_identifier(table_name)}'
                )
                export_path = target_path.parent / file_name
                temporary_path = export_path.with_suffix(export_path.suffix + ".tmp")

                try:
                    con.execute(
                        f"COPY (SELECT {column_list} FROM {qualified_table}) "
                        f"TO {_quote_sql_literal(str(temporary_path))} "
                        "(FORMAT PARQUET, COMPRESSION ZSTD)"
                    )
                    temporary_path.replace(export_path)
                finally:
                    if temporary_path.exists():
                        temporary_path.unlink()

                row_count = con.execute(
                    f"SELECT COUNT(*) FROM {qualified_table}"
                ).fetchone()[0]
                sections.append(
                    f"| `CherryMon`.`main`.`{table_name}` | "
                    f"`{file_name}` | {row_count} |"
                )
            sections.append("")
    except Exception as exc:  # pragma: no cover - depends on local DB lock state
        sections.append("## Access note")
        sections.append("")
        sections.append(
            f"Metadata could not be read from the database because: `{exc}`"
        )
        sections.append("")
        sections.append("Please close any other process using the DuckDB file and rerun the export.")

    target_path.write_text("\n".join(sections), encoding="utf-8")
    return target_path
