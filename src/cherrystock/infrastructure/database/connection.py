from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import os

import duckdb

from cherrystock.config.settings import settings


class DuckDBConnectionFactory:
    """Create short-lived DuckDB connections for read and write workloads."""

    def __init__(
        self,
        db_path: Path | None = None,
        *,
        duckdb_env: str | None = None,
        motherduck_token: str | None = None,
    ) -> None:
        self._explicit_db_path = db_path is not None
        self._db_path = (db_path or settings.local_db_path).expanduser()
        self._duckdb_env = (duckdb_env or settings.duckdb_env or "local").strip().lower()
        self._motherduck_token = motherduck_token if motherduck_token is not None else settings.motherduck_token

    def _connect(self, *, read_only: bool) -> duckdb.DuckDBPyConnection:
        env_override = (os.getenv("DUCKDB_ENV") or "").strip().lower()
        target_env = env_override or self._duckdb_env

        if target_env == "cloud":
            token = (os.getenv("MOTHERDUCK_TOKEN") or self._motherduck_token or "").strip()
            return duckdb.connect(f"md:?token={token}")

        db_path_override = os.getenv("LOCAL_DB_PATH")
        if self._explicit_db_path:
            target_path = self._db_path
        else:
            target_path = Path(db_path_override).expanduser() if db_path_override else self._db_path
        return duckdb.connect(str(target_path), read_only=read_only)

    def create_reader(self) -> duckdb.DuckDBPyConnection:
        return self._connect(read_only=True)

    def create_writer(self) -> duckdb.DuckDBPyConnection:
        return self._connect(read_only=False)

    @contextmanager
    def reader(self) -> Iterator[duckdb.DuckDBPyConnection]:
        conn = self.create_reader()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def writer(self) -> Iterator[duckdb.DuckDBPyConnection]:
        conn = self.create_writer()
        try:
            yield conn
        finally:
            conn.close()
