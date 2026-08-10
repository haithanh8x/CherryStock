from pathlib import Path

from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


def _seed_schema(factory: DuckDBConnectionFactory) -> None:
    with factory.writer() as con:
        con.execute("CREATE TABLE IF NOT EXISTS run_audit (id INTEGER PRIMARY KEY, stage VARCHAR)")


def _count_rows(factory: DuckDBConnectionFactory) -> int:
    with factory.reader() as con:
        return int(con.execute("SELECT COUNT(*) FROM run_audit").fetchone()[0])


def _run_like_write_flow(factory: DuckDBConnectionFactory, fail_midway: bool) -> None:
    with DuckDBUnitOfWork(factory) as uow:
        assert uow.connection is not None
        uow.connection.execute("INSERT INTO run_audit (id, stage) VALUES (1, 'start')")

        if fail_midway:
            raise RuntimeError("forced failure in write flow")

        uow.connection.execute("INSERT INTO run_audit (id, stage) VALUES (2, 'end')")


def test_run_like_write_flow_rolls_back_when_midway_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "run_like_rollback.duckdb"
    factory = DuckDBConnectionFactory(db_path=db_path)
    _seed_schema(factory)

    try:
        _run_like_write_flow(factory=factory, fail_midway=True)
    except RuntimeError:
        pass

    assert _count_rows(factory) == 0


def test_run_like_write_flow_commits_when_successful(tmp_path: Path) -> None:
    db_path = tmp_path / "run_like_commit.duckdb"
    factory = DuckDBConnectionFactory(db_path=db_path)
    _seed_schema(factory)

    _run_like_write_flow(factory=factory, fail_midway=False)

    assert _count_rows(factory) == 2
