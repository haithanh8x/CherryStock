from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"

# Load repository-level environment values when present.
load_dotenv(PROJECT_ROOT / ".env")


def _as_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _default_data_dir() -> Path:
    env_data_dir = _as_optional_str(os.getenv("DATA_DIR"))
    if env_data_dir:
        return Path(env_data_dir).expanduser()

    env_datafile_path = _as_optional_str(os.getenv("DATAFILE_PATH"))
    if env_datafile_path:
        return Path(env_datafile_path).expanduser()

    repo_data_dir = PROJECT_ROOT / "data"
    if repo_data_dir.exists():
        return repo_data_dir

    one_drive = _as_optional_str(os.getenv("OneDrive"))
    if one_drive:
        return Path(one_drive).expanduser() / "Datafile"

    return repo_data_dir


@dataclass(frozen=True)
class Settings:
    project_root: Path
    src_root: Path
    data_dir: Path
    local_db_path: Path
    datafile_path: Path
    datafile_folder: str
    agent_path: Path
    duckdb_sql_path: Path
    amibroker_database_path: Path | None
    amibroker_root: Path
    amibroker_log_path: Path
    amibroker_afl_path: Path
    amibroker_eod_path: Path
    amibroker_intraday_path: Path
    amibroker_eod_targets: tuple[tuple[Path, str], ...]
    amibroker_intraday_targets: tuple[tuple[Path, str], ...]
    motherduck_path: str | None
    motherduck_token: str | None
    duckdb_env: str


def load_settings() -> Settings:
    data_dir = _default_data_dir()

    local_db_env = _as_optional_str(os.getenv("LOCAL_DB_PATH"))
    local_db_path = Path(local_db_env).expanduser() if local_db_env else data_dir / "CherryMon.duckdb"

    agent_env = _as_optional_str(os.getenv("AGENT_PATH"))
    agent_path = Path(agent_env).expanduser() if agent_env else PROJECT_ROOT / ".github" / "agents"

    sql_env = _as_optional_str(os.getenv("DUCKDB_SQL_PATH"))
    duckdb_sql_path = Path(sql_env).expanduser() if sql_env else SRC_ROOT / "DuckDB" / "sql"

    amibroker_db_env = _as_optional_str(os.getenv("AMIBROKER_DATABASE_PATH"))
    amibroker_database_path: Path | None = None
    if amibroker_db_env:
        candidate = Path(amibroker_db_env).expanduser()
        # Guard against stale/misconfigured Windows environment variables that
        # point AMIBROKER_DATABASE_PATH at the DuckDB file. AmiBroker databases
        # are directories; a .duckdb file must never be passed to LoadDatabase().
        if candidate.suffix.lower() != ".duckdb":
            amibroker_database_path = candidate

    amibroker_root_env = _as_optional_str(os.getenv("AMIBROKER_ROOT"))
    amibroker_root = (
        Path(amibroker_root_env).expanduser()
        if amibroker_root_env
        else Path("C:/Program1/AmiBroker")
    )

    amibroker_log_env = _as_optional_str(os.getenv("AMIBROKER_LOG_PATH"))
    amibroker_log_path = (
        Path(amibroker_log_env).expanduser()
        if amibroker_log_env
        else (amibroker_root / "broker.log")
    )

    amibroker_afl_env = _as_optional_str(os.getenv("AMIBROKER_AFL_PATH"))
    amibroker_afl_path = (
        Path(amibroker_afl_env).expanduser()
        if amibroker_afl_env
        else (PROJECT_ROOT / "src" / "Amibroker" / "Formulas" / "CherryMon")
    )

    amibroker_eod_env = _as_optional_str(os.getenv("AMIBROKER_EOD_PATH"))
    amibroker_eod_path = (
        Path(amibroker_eod_env).expanduser()
        if amibroker_eod_env
        else (amibroker_root / "Data_FireAnt" / "AmiBroker" / "EOD")
    )

    amibroker_intraday_env = _as_optional_str(os.getenv("AMIBROKER_INTRADAY_PATH"))
    amibroker_intraday_path = (
        Path(amibroker_intraday_env).expanduser()
        if amibroker_intraday_env
        else (amibroker_root / "Data_FireAnt" / "AmiBroker" / "Intraday")
    )

    amibroker_eod_targets = (
        (amibroker_eod_path / "active", "raw_active_eod"),
        (amibroker_eod_path / "commodity", "raw_commodity_eod"),
        (amibroker_eod_path / "foreign", "raw_foreign_eod"),
        (amibroker_eod_path / "futures", "raw_futures_eod"),
        (amibroker_eod_path / "index", "raw_index_eod"),
        (amibroker_eod_path / "industry", "raw_industry_eod"),
        (amibroker_eod_path / "market", "raw_market_eod"),
        (amibroker_eod_path / "other", "raw_other_eod"),
        (amibroker_eod_path / "prop", "raw_prop_eod"),
        (amibroker_eod_path / "stock", "raw_stock_eod"),
        (amibroker_eod_path / "supplydemand", "raw_supplydemand_eod"),
        (amibroker_eod_path / "warrant", "raw_warrant_eod"),
    )

    amibroker_intraday_targets = (
        (amibroker_intraday_path / "futures", "raw_futures_intraday"),
        (amibroker_intraday_path / "index", "raw_index_intraday"),
        (amibroker_intraday_path / "stock", "raw_stock_intraday"),
        (amibroker_intraday_path / "warrant", "raw_warrant_intraday"),
    )

    datafile_env = _as_optional_str(os.getenv("DATAFILE_PATH"))
    datafile_path = Path(datafile_env).expanduser() if datafile_env else data_dir

    datafile_folder = str(datafile_path)
    if not datafile_folder.endswith(("/", "\\")):
        datafile_folder = f"{datafile_folder}{os.sep}"

    return Settings(
        project_root=PROJECT_ROOT,
        src_root=SRC_ROOT,
        data_dir=data_dir,
        local_db_path=local_db_path,
        datafile_path=datafile_path,
        datafile_folder=datafile_folder,
        agent_path=agent_path,
        duckdb_sql_path=duckdb_sql_path,
        amibroker_database_path=amibroker_database_path,
        amibroker_root=amibroker_root,
        amibroker_log_path=amibroker_log_path,
        amibroker_afl_path=amibroker_afl_path,
        amibroker_eod_path=amibroker_eod_path,
        amibroker_intraday_path=amibroker_intraday_path,
        amibroker_eod_targets=amibroker_eod_targets,
        amibroker_intraday_targets=amibroker_intraday_targets,
        motherduck_path=_as_optional_str(os.getenv("DB_MOTHERDUCK_PATH")) or "md:CherryMon",
        motherduck_token=_as_optional_str(os.getenv("MOTHERDUCK_TOKEN")),
        duckdb_env=(_as_optional_str(os.getenv("DUCKDB_ENV")) or "local").lower(),
    )


settings = load_settings()
