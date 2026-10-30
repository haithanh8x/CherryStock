"""Synchronize Indicator metadata from Export_Indicator.afl without touching fact tables.

Usage:
    python -m scripts.sync_afl_indicator_metadata
    python -m scripts.sync_afl_indicator_metadata --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cherrystock.config.settings import settings
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from scripts.sync_amibroker_indicator_full import (
    DEFAULT_AFL, SPECS, _ensure_metadata, COMPONENTS, CONFIGS,
)


def sync(connection, afl_path: Path, *, dry_run: bool = False) -> dict:
    """Validate the AFL export contract, then upsert dimensions transactionally."""
    source = afl_path.read_text(encoding="utf-8")
    # Only exported AddColumn labels count; internal intermediate variables do not.
    declared = set(re.findall(
        r'AddColumn\s*\([^;]*?\,\s*"([A-Za-z0-9_]+)"\s*\+\s*suffix\s*,',
        source, flags=re.DOTALL,
    ))
    # OHLC price columns are exported for context, not indicator metadata.
    price_columns = {"OPEN_", "HIGH_", "LOW_", "CLOSE_"}
    indicator_columns = declared - price_columns
    expected = {spec.csv_column.rsplit("_", 1)[0] + "_" for spec in SPECS}
    if indicator_columns != expected:
        raise ValueError(
            f"AFL export metadata mismatch: missing={sorted(expected-indicator_columns)}, "
            f"unexpected={sorted(indicator_columns-expected)}"
        )
    for tf, token in (("D", "inDaily"), ("W", "inWeekly"), ("M", "inMonthly")):
        if not re.search(rf'CS_ExportIndicators\s*\(\s*{token}\s*,\s*"{tf}"', source):
            raise ValueError(f"AFL missing {tf} timeframe export")
    configs = {s.config_code for s in SPECS}
    components = {(s.indicator_code, s.component) for s in SPECS}
    result = {
        "afl": str(afl_path),
        "export_columns": len(SPECS),
        "price_columns_excluded": sorted(declared & price_columns),
        "configs": len(configs),
        "components": len(components),
        "dry_run": dry_run,
    }
    if dry_run:
        return result
    connection.execute("BEGIN TRANSACTION")
    try:
        _ensure_metadata(connection)
        missing_configs = [c for c in configs if connection.execute(
            f"SELECT COUNT(*) FROM {CONFIGS} WHERE ConfigCode = ?", [c]
        ).fetchone()[0] != 1]
        missing_components = [c for c in components if connection.execute(
            f"SELECT COUNT(*) FROM {COMPONENTS} WHERE IndicatorCode=? AND ComponentCode=?",
            list(c)
        ).fetchone()[0] != 1]
        if missing_configs or missing_components:
            raise RuntimeError(
                f"Metadata verification failed: configs={missing_configs}, "
                f"components={missing_components}"
            )
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--afl", type=Path, default=DEFAULT_AFL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.writer() as connection:
        print("[AFL METADATA]", sync(connection, args.afl, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
