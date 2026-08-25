"""Seed ``dim_indicator_config`` for active indicators in ``dim_indicator_component``.

Generates executable configs per Indicator_Engine.md section 21 for the
indicators currently active, across Daily / Weekly / Monthly timeframes.

Idempotent: rerunning updates existing ConfigCode rows, no duplicates.

Usage:
    .venv\\Scripts\\python.exe scripts\\seed_dim_indicator_config.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from Ults.DuckLib import DuckDBManager  # noqa: E402

DIM_INDICATOR = '"CherryMon"."main"."dim_indicator"'
DIM_COMPONENT = '"CherryMon"."main"."dim_indicator_component"'
DIM_CONFIG = '"CherryMon"."main"."dim_indicator_config"'

TIMEFRAMES = ("D", "W", "M")

# Config templates: IndicatorCode -> list of (suffix, parameters dict, warmup bars).
# ConfigCode is built as f"{IndicatorCode}{suffix}_{Timeframe}".
CONFIG_TEMPLATES: dict[str, list[tuple[str, dict, int]]] = {
    "MA": [
        ("20", {"length": 20}, 20),
        ("50", {"length": 50}, 50),
        ("100", {"length": 100}, 100),
        ("200", {"length": 200}, 200),
    ],
    "RSI": [
        ("14", {"length": 14}, 14),
    ],
    "BB": [
        ("20_2", {"length": 20, "std": 2.0}, 20),
    ],
}


def build_config_rows() -> list[tuple[str, str, str, str, int]]:
    """Build config rows for every indicator present in dim_indicator_component."""
    con = DuckDBManager.get_connection(read_only=True)
    try:
        active_codes = [
            row[0]
            for row in con.execute(
                f"""
                SELECT DISTINCT di.IndicatorCode
                FROM {DIM_INDICATOR} di
                JOIN {DIM_COMPONENT} dic ON dic.IndicatorCode = di.IndicatorCode
                WHERE di.IsActive = TRUE AND dic.IsActive = TRUE
                """
            ).fetchall()
        ]
    finally:
        DuckDBManager.close_connection(con)

    if not active_codes:
        raise ValueError("Không có indicator nào active trong dim_indicator_component.")

    rows: list[tuple[str, str, str, str, int]] = []
    for code in sorted(active_codes):
        templates = CONFIG_TEMPLATES.get(code)
        if templates is None:
            print(f"[seed_dim_indicator_config] skip {code}: no config template")
            continue
        for timeframe in TIMEFRAMES:
            for suffix, params, warmup in templates:
                rows.append(
                    (
                        f"{code}{suffix}_{timeframe}",
                        code,
                        timeframe,
                        json.dumps(params),
                        warmup,
                    )
                )
    return rows


def upsert_dim_indicator_config(rows: list[tuple]) -> int:
    """Upsert config rows; returns total row count after upsert."""
    con = DuckDBManager.get_connection(read_only=False)
    try:
        con.execute(
            f"""
            CREATE SEQUENCE IF NOT EXISTS seq_indicator_config START 1
            """
        )
        con.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DIM_CONFIG} (
                ConfigId            BIGINT NOT NULL DEFAULT nextval('seq_indicator_config'),
                ConfigCode          VARCHAR NOT NULL,
                IndicatorCode       VARCHAR NOT NULL,
                Timeframe           VARCHAR NOT NULL,
                Parameters          JSON NOT NULL,
                WarmupBars          INTEGER,
                IsEnabled           BOOLEAN NOT NULL DEFAULT TRUE,
                Description         VARCHAR,
                CreatedAt           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt           TIMESTAMP,
                PRIMARY KEY (ConfigId),
                UNIQUE (ConfigCode)
            )
            """
        )

        con.executemany(
            f"""
            INSERT INTO {DIM_CONFIG} (
                ConfigCode, IndicatorCode, Timeframe,
                Parameters, WarmupBars, IsEnabled
            )
            VALUES (?, ?, ?, ?, ?, TRUE)
            ON CONFLICT (ConfigCode) DO UPDATE SET
                Parameters = EXCLUDED.Parameters,
                WarmupBars = EXCLUDED.WarmupBars,
                IsEnabled = TRUE,
                UpdatedAt = now()
            """,
            rows,
        )
        con.commit()

        total = con.execute(f"SELECT COUNT(*) FROM {DIM_CONFIG}").fetchone()[0]
        print(f"[seed_dim_indicator_config] upserted={len(rows)}, total={total}")
        return total
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        DuckDBManager.close_connection(con)


def main() -> int:
    print("[seed_dim_indicator_config] start")
    rows = build_config_rows()
    print(f"[seed_dim_indicator_config] built rows: {len(rows)}")
    upsert_dim_indicator_config(rows)
    print("[seed_dim_indicator_config] success")
    return 0


if __name__ == "__main__":
    sys.exit(main())
