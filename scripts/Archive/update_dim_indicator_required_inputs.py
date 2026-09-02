"""Update RequiredInputs metadata for CherryMon.main.dim_indicator.

The script derives required OHLCV inputs from the configured pandas-ta-classic
FunctionName and applies explicit overrides for indicators whose signatures
contain optional source columns or whose semantic requirements are clearer than
signature introspection alone.

Safety characteristics:
- Reads all IndicatorCode/FunctionName rows first.
- Resolves RequiredInputs for every row before writing anything.
- Fails if any indicator cannot be resolved.
- Updates inside one transaction.
- Stores RequiredInputs as JSON arrays using CherryStock column names:
  Open, High, Low, Close, Volume.
- Rerunning is idempotent.

Usage:
    .venv\\Scripts\\python.exe scripts\\update_dim_indicator_required_inputs.py
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas_ta_classic as ta  # noqa: E402

from Ults.DuckLib import DuckDBManager  # noqa: E402

TARGET_TABLE = '"CherryMon"."main"."dim_indicator"'

SOURCE_PARAM_TO_COLUMN = {
    "open": "Open",
    "open_": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "volume": "Volume",
}

# Explicit semantic mappings for indicators where relying only on Python
# signature inspection could include optional/non-essential source fields or
# miss the intended CherryStock input contract.
REQUIRED_INPUTS_BY_CODE: dict[str, tuple[str, ...]] = {
    # Trend / momentum using Close only
    "MA": ("Close",),
    "EMA": ("Close",),
    "WMA": ("Close",),
    "DEMA": ("Close",),
    "TEMA": ("Close",),
    "TRIMA": ("Close",),
    "KAMA": ("Close",),
    "ALMA": ("Close",),
    "HMA": ("Close",),
    "ZLMA": ("Close",),
    "JMA": ("Close",),
    "T3": ("Close",),
    "VIDYA": ("Close",),
    "FWMA": ("Close",),
    "SINWMA": ("Close",),
    "RSI": ("Close",),
    "RSX": ("Close",),
    "LRSI": ("Close",),
    "CMO": ("Close",),
    "MOM": ("Close",),
    "ROC": ("Close",),
    "PPO": ("Close",),
    "TSI": ("Close",),
    "TRIX": ("Close",),
    "APO": ("Close",),
    "CTI": ("Close",),
    "COPPOCK": ("Close",),
    "CG": ("Close",),
    "DPO": ("Close",),
    "ER": ("Close",),
    "EBSW": ("Close",),
    "INERTIA": ("Close",),
    "SLOPE": ("Close",),
    "LINREG": ("Close",),
    "LINREG_SLOPE": ("Close",),
    "VHF": ("Close",),
    "BIAS": ("Close",),
    "PSL": ("Close",),
    "QQE": ("Close",),
    "STC": ("Close",),
    "SMI": ("Close",),
    "CFO": ("Close",),
    "FOSC": ("Close",),
    "PO": ("Close",),
    "MD": ("Close",),
    "TD_SEQ": ("Close",),
    "BB": ("Close",),
    "MACD": ("Close",),
    "UI": ("Close",),
    "ENTROPY": ("Close",),
    "MAD": ("Close",),
    "MEDIAN": ("Close",),
    "QUANTILE": ("Close",),
    "VARIANCE": ("Close",),
    "SKEW": ("Close",),
    "KURTOSIS": ("Close",),
    "STDEV": ("Close",),
    "ZSCORE": ("Close",),
    "HWC": ("Close",),
    "HWMA": ("Close",),
    "SSF": ("Close",),
    "RMA": ("Close",),
    "MCGD": ("Close",),
    "PMAX": ("Close",),
    "KST": ("Close",),
    "STDERR": ("Close",),
    "TSF": ("Close",),
    "MIDPOINT": ("Close",),
    "DECAY": ("Close",),
    "EDECAY": ("Close",),
    "INCREASING": ("Close",),
    "DECREASING": ("Close",),
    "SIGNED_SERIES": ("Close",),

    # High / Low / Close based
    "ADX": ("High", "Low", "Close"),
    "ATR": ("High", "Low", "Close"),
    "NATR": ("High", "Low", "Close"),
    "TRUE_RANGE": ("High", "Low", "Close"),
    "UO": ("High", "Low", "Close"),
    "CCI": ("High", "Low", "Close"),
    "WR": ("High", "Low", "Close"),
    "ERI": ("High", "Low", "Close"),
    "PGO": ("High", "Low", "Close"),
    "WAD": ("High", "Low", "Close"),
    "STOCH": ("High", "Low", "Close"),
    "STOCHF": ("High", "Low", "Close"),
    "KDJ": ("High", "Low", "Close"),
    "ICHIMOKU": ("High", "Low", "Close"),
    "SUPERTREND": ("High", "Low", "Close"),
    "PSAR": ("High", "Low", "Close"),
    "KC": ("High", "Low", "Close"),
    "ACCBANDS": ("High", "Low", "Close"),
    "SQUEEZE": ("High", "Low", "Close"),
    "SQUEEZE_PRO": ("High", "Low", "Close"),
    "ABERRATION": ("High", "Low", "Close"),
    "HILO": ("High", "Low", "Close"),
    "VORTEX": ("High", "Low", "Close"),
    "TYPPRICE": ("High", "Low", "Close"),
    "HLC3": ("High", "Low", "Close"),
    "WCP": ("High", "Low", "Close"),

    # High / Low based
    "DMI": ("High", "Low"),
    "AO": ("High", "Low"),
    "FISHER": ("High", "Low"),
    "AROON": ("High", "Low"),
    "DONCHIAN": ("High", "Low"),
    "MASSI": ("High", "Low"),
    "THERMO": ("High", "Low"),
    "CVI": ("High", "Low"),
    "MEDPRICE": ("High", "Low"),
    "HL2": ("High", "Low"),
    "MIDPRICE": ("High", "Low"),

    # Close + Volume
    "VWMA": ("Close", "Volume"),
    "OBV": ("Close", "Volume"),
    "EFI": ("Close", "Volume"),
    "PVT": ("Close", "Volume"),
    "PVOL": ("Close", "Volume"),
    "PVR": ("Close", "Volume"),
    "NVI": ("Close", "Volume"),
    "PVI": ("Close", "Volume"),

    # Volume only
    "PVO": ("Volume",),
    "VOSC": ("Volume",),

    # High + Low + Volume
    "EMV": ("High", "Low", "Volume"),
    "EOM": ("High", "Low", "Volume"),
    "MARKETFI": ("High", "Low", "Volume"),

    # High + Low + Close + Volume
    "MFI": ("High", "Low", "Close", "Volume"),
    "CMF": ("High", "Low", "Close", "Volume"),
    "AD": ("High", "Low", "Close", "Volume"),
    "ADOSC": ("High", "Low", "Close", "Volume"),
    "KVO": ("High", "Low", "Close", "Volume"),
    "VFI": ("High", "Low", "Close", "Volume"),
    "VWAP": ("High", "Low", "Close", "Volume"),

    # Open + Close
    "QSTICK": ("Open", "Close"),

    # OHLC
    "BRAR": ("Open", "High", "Low", "Close"),
    "HA": ("Open", "High", "Low", "Close"),
    "RVGI": ("Open", "High", "Low", "Close"),
    "BOP": ("Open", "High", "Low", "Close"),
    "AVGPRICE": ("Open", "High", "Low", "Close"),
    "OHLC4": ("Open", "High", "Low", "Close"),
    "CDL_PATTERN": ("Open", "High", "Low", "Close"),

    # Close-derived oscillator
    "STOCHRSI": ("Close",),
}


def _infer_inputs_from_function(function_name: str) -> tuple[str, ...]:
    """Infer OHLCV source columns from a pandas-ta-classic function signature."""
    if not function_name:
        return ()

    function = getattr(ta, function_name, None)
    if function is None:
        return ()

    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return ()

    resolved: list[str] = []
    for parameter_name in signature.parameters:
        source_column = SOURCE_PARAM_TO_COLUMN.get(parameter_name.lower())
        if source_column is not None and source_column not in resolved:
            resolved.append(source_column)

    return tuple(resolved)


def _resolve_required_inputs(indicator_code: str, function_name: str) -> tuple[str, ...]:
    """Resolve the RequiredInputs contract for one dim_indicator row."""
    code = indicator_code.strip().upper()

    explicit = REQUIRED_INPUTS_BY_CODE.get(code)
    if explicit is not None:
        return explicit

    inferred = _infer_inputs_from_function(function_name)
    if inferred:
        return inferred

    raise ValueError(
        f"Không xác định được RequiredInputs cho IndicatorCode={indicator_code!r}, "
        f"FunctionName={function_name!r}. Hãy thêm mapping explicit trước khi chạy lại."
    )


def update_dim_indicator_required_inputs() -> int:
    """Update RequiredInputs for every row in CherryMon.main.dim_indicator."""
    con = DuckDBManager.get_connection(read_only=False)
    try:
        rows = con.sql(
            f"""
            SELECT
                IndicatorCode,
                FunctionName
            FROM {TARGET_TABLE}
            ORDER BY IndicatorCode
            """
        ).fetchall()

        if not rows:
            raise ValueError(f"{TARGET_TABLE} không có dữ liệu để cập nhật.")

        updates: list[tuple[str, str]] = []
        for indicator_code, function_name in rows:
            required_inputs = _resolve_required_inputs(
                indicator_code=str(indicator_code),
                function_name=str(function_name or ""),
            )
            updates.append(
                (
                    json.dumps(required_inputs, ensure_ascii=False),
                    str(indicator_code),
                )
            )

        # Resolve every indicator before opening the write transaction so that
        # an unknown mapping cannot leave a partially updated table.
        con.execute("BEGIN TRANSACTION")
        try:
            con.executemany(
                f"""
                UPDATE {TARGET_TABLE}
                SET
                    RequiredInputs = ?::JSON,
                    UpdatedAt = CURRENT_TIMESTAMP
                WHERE IndicatorCode = ?
                """,
                updates,
            )

            invalid_count = con.sql(
                f"""
                SELECT count(*)
                FROM {TARGET_TABLE}
                WHERE RequiredInputs IS NULL
                   OR json_array_length(RequiredInputs) = 0
                """
            ).fetchone()[0]

            if invalid_count:
                raise RuntimeError(
                    f"Validation thất bại: còn {invalid_count} indicator có RequiredInputs rỗng/NULL."
                )

            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        print(f"Updated RequiredInputs for {len(updates)} indicators in {TARGET_TABLE}.")

        preview = con.sql(
            f"""
            SELECT
                IndicatorCode,
                FunctionName,
                RequiredInputs
            FROM {TARGET_TABLE}
            ORDER BY IndicatorCode
            """
        ).df()
        print(preview.to_string(index=False))

        return len(updates)
    finally:
        DuckDBManager.close_connection(con)


def main() -> None:
    update_dim_indicator_required_inputs()


if __name__ == "__main__":
    main()
