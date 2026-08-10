from pathlib import Path

from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


def _count_rows(factory: DuckDBConnectionFactory, table_name: str) -> int:
    with factory.reader() as con:
        return int(con.execute(f"SELECT COUNT(*) AS n FROM {table_name}").fetchone()[0])


def test_unit_of_work_commits_on_success(tmp_path: Path) -> None:
    db_path = tmp_path / "uow_commit.duckdb"
    factory = DuckDBConnectionFactory(db_path=db_path)

    with DuckDBUnitOfWork(factory) as uow:
        assert uow.connection is not None
        uow.connection.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, value VARCHAR)")
        uow.connection.execute("INSERT INTO t (id, value) VALUES (1, 'ok')")

    assert _count_rows(factory, "t") == 1


def test_unit_of_work_rolls_back_on_error(tmp_path: Path) -> None:
    db_path = tmp_path / "uow_rollback.duckdb"
    factory = DuckDBConnectionFactory(db_path=db_path)

    with factory.writer() as con:
        con.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, value VARCHAR)")
        con.execute("INSERT INTO t (id, value) VALUES (1, 'ok')")

    try:
        with DuckDBUnitOfWork(factory) as uow:
            assert uow.connection is not None
            uow.connection.execute("INSERT INTO t (id, value) VALUES (2, 'will_rollback')")
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    assert _count_rows(factory, "t") == 1
