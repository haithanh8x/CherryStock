"""Seed ``dim_indicator_component`` for active indicators in ``dim_indicator``.

Single-output indicators get a ``VALUE`` component; known multi-output
indicators get normalized component mappings. V2.0 also seeds generic
ValueSemantic/Unit metadata used by downstream R/S providers.

Idempotent: rerunning updates existing keys, no duplicates.

Usage:
    .venv\\Scripts\\python.exe scripts\\seed_dim_indicator_component.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from Ults.DuckLib import DuckDBManager  # noqa: E402

DIM_INDICATOR = '"CherryMon"."main"."dim_indicator"'
DIM_COMPONENT = '"CherryMon"."main"."dim_indicator_component"'

# Multi-output component mapping: IndicatorCode -> list of
# (ComponentCode, ComponentName, OutputPrefix, SortOrder, IsPrimary)
MULTI_OUTPUT_COMPONENTS: dict[str, list[tuple[str, str, str | None, int, bool]]] = {
    "BB": [
        ("LOWER", "Lower Band", "BBL", 1, False),
        ("MIDDLE", "Middle Band", "BBM", 2, False),
        ("UPPER", "Upper Band", "BBU", 3, True),
        ("WIDTH", "Band Width", "BBB", 4, False),
        ("PERCENT", "Percent Position", "BBP", 5, False),
    ],
    "MACD": [
        ("LINE", "MACD Line", "MACD", 1, True),
        ("SIGNAL", "Signal Line", "MACDs", 2, False),
        ("HIST", "Histogram", "MACDh", 3, False),
    ],
    "ADX": [
        ("ADX", "Average Directional Index", "ADX", 1, True),
        ("PLUS_DI", "Plus Directional Indicator", "DMP", 2, False),
        ("MINUS_DI", "Minus Directional Indicator", "DMN", 3, False),
    ],
    "STOCH": [
        ("K", "%K Line", "STOCHk", 1, True),
        ("D", "%D Line", "STOCHd", 2, False),
    ],
}

# Generic component semantics. Keep R/S-specific role/family outside Indicator Engine.
COMPONENT_SEMANTICS: dict[tuple[str, str], tuple[str, str]] = {
    ("MA", "VALUE"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "LOWER"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "MIDDLE"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "UPPER"): ("PRICE_LEVEL", "PRICE"),
    ("BB", "WIDTH"): ("VOLATILITY", "PERCENT"),
    ("BB", "PERCENT"): ("RATIO", "RATIO"),
    ("RSI", "VALUE"): ("OSCILLATOR", "INDEX"),
    ("ATR", "VALUE"): ("VOLATILITY_DISTANCE", "PRICE"),
    ("OBV", "VALUE"): ("CUMULATIVE_FLOW", "VOLUME"),
    ("AD", "VALUE"): ("CUMULATIVE_FLOW", "VOLUME"),
}


def build_component_rows() -> list[
    tuple[str, str, str, str | None, int, bool, str | None, str | None]
]:
    """Build component rows for every active indicator in dim_indicator."""
    con = DuckDBManager.get_connection(read_only=True)
    try:
        active_codes = [
            row[0]
            for row in con.execute(
                f"SELECT IndicatorCode FROM {DIM_INDICATOR} WHERE IsActive = TRUE"
            ).fetchall()
        ]
    finally:
        DuckDBManager.close_connection(con)

    if not active_codes:
        raise ValueError("Không có indicator nào IsActive=TRUE trong dim_indicator.")

    rows: list[
        tuple[str, str, str, str | None, int, bool, str | None, str | None]
    ] = []
    for code in active_codes:
        components = MULTI_OUTPUT_COMPONENTS.get(code)
        if components is None:
            semantic, unit = COMPONENT_SEMANTICS.get((code, "VALUE"), (None, None))
            rows.append(
                (code, "VALUE", f"{code} Value", None, 1, True, semantic, unit)
            )
        else:
            for comp_code, comp_name, prefix, order, is_primary in components:
                semantic, unit = COMPONENT_SEMANTICS.get(
                    (code, comp_code), (None, None)
                )
                rows.append(
                    (
                        code,
                        comp_code,
                        comp_name,
                        prefix,
                        order,
                        is_primary,
                        semantic,
                        unit,
                    )
                )

    return rows


def upsert_dim_indicator_component(rows: list[tuple]) -> int:
    """Upsert component rows; returns total row count after upsert."""
    con = DuckDBManager.get_connection(read_only=False)
    try:
        con.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DIM_COMPONENT} (
                IndicatorCode       VARCHAR NOT NULL,
                ComponentCode       VARCHAR NOT NULL,
                ComponentName       VARCHAR NOT NULL,
                OutputPrefix        VARCHAR,
                SortOrder           INTEGER,
                ValueSemantic       VARCHAR,
                Unit                VARCHAR,
                IsPrimary           BOOLEAN NOT NULL DEFAULT FALSE,
                IsActive            BOOLEAN NOT NULL DEFAULT TRUE,
                PRIMARY KEY (IndicatorCode, ComponentCode)
            )
            """
        )

        con.executemany(
            f"""
            INSERT INTO {DIM_COMPONENT} (
                IndicatorCode, ComponentCode, ComponentName,
                OutputPrefix, SortOrder, IsPrimary,
                ValueSemantic, Unit, IsActive
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRUE)
            ON CONFLICT (IndicatorCode, ComponentCode) DO UPDATE SET
                ComponentName = EXCLUDED.ComponentName,
                OutputPrefix = EXCLUDED.OutputPrefix,
                SortOrder = EXCLUDED.SortOrder,
                IsPrimary = EXCLUDED.IsPrimary,
                ValueSemantic = COALESCE(EXCLUDED.ValueSemantic, ValueSemantic),
                Unit = COALESCE(EXCLUDED.Unit, Unit),
                IsActive = TRUE
            """,
            rows,
        )
        con.commit()

        total = con.execute(f"SELECT COUNT(*) FROM {DIM_COMPONENT}").fetchone()[0]
        print(
            f"[seed_dim_indicator_component] upserted={len(rows)}, total={total}"
        )
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
    print("[seed_dim_indicator_component] start")
    rows = build_component_rows()
    print(f"[seed_dim_indicator_component] built rows: {len(rows)}")
    upsert_dim_indicator_component(rows)
    print("[seed_dim_indicator_component] success")
    return 0


if __name__ == "__main__":
    sys.exit(main())
