"""Seed ``dim_indicator`` from the indicator master list Excel.

Reads ``.github/agents/lstIndicators.xlsx`` (sheet ``Indicators``), maps each
row to a pandas-ta-classic function via an explicit whitelist registry, and
upserts into ``"CherryMon"."main"."dim_indicator"``.

Idempotent: rerunning updates existing IndicatorCode rows, no duplicates.

Usage:
    .venv\\Scripts\\python.exe scripts\\seed_dim_indicator.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas_ta_classic as ta  # noqa: E402

from Ults.DuckLib import DuckDBManager  # noqa: E402

EXCEL_PATH = PROJECT_ROOT / ".github" / "agents" / "lstIndicators.xlsx"
SHEET_NAME = "Indicators"
TARGET_TABLE = '"CherryMon"."main"."dim_indicator"'

# Whitelist registry: IndicatorCode -> pandas-ta-classic function name.
# Only indicators resolvable in the installed library are seeded as active;
# rows without a mapping are skipped and reported.
INDICATOR_REGISTRY: dict[str, str] = {
    # Single output - Close based
    "MA": "sma",
    "EMA": "ema",
    "WMA": "wma",
    "DEMA": "dema",
    "TEMA": "tema",
    "TRIMA": "trima",
    "KAMA": "kama",
    "ALMA": "alma",
    "HMA": "hma",
    "ZLMA": "zlma",
    "JMA": "jma",
    "T3": "t3",
    "VIDYA": "vidya",
    "FWMA": "fwma",
    "SINWMA": "sinwma",
    "VWMA": "vwma",
    "RSI": "rsi",
    "RSX": "rsx",
    "LRSI": "lrsi",
    "CONNORS_RSI": None,  # not available -> skip
    "CMO": "cmo",
    "MOM": "mom",
    "ROC": "roc",
    "PPO": "ppo",
    "PVO": "pvo",
    "TSI": "tsi",
    "TRIX": "trix",
    "UO": "uo",
    "AO": "ao",
    "APO": "apo",
    "CCI": "cci",
    "WR": "willr",
    "QSTICK": "qstick",
    "CTI": "cti",
    "COPPOCK": "coppock",
    "FISHER": "fisher",
    "CG": "cg",
    "DPO": "dpo",
    "ER": "er",
    "ERI": "eri",
    "EBSW": "ebsw",
    "INERTIA": "inertia",
    "SLOPE": "slope",
    "LINREG": "linreg",
    "LINREG_SLOPE": "linregslope",
    "VHF": "vhf",
    "BIAS": "bias",
    "BRAR": "brar",
    "PSL": "psl",
    "QQE": "qqe",
    "STC": "stc",
    "SMI": "smi",
    "PGO": "pgo",
    "CFO": "cfo",
    "FOSC": "fosc",
    "PO": "po",
    "MD": "md",
    "TD_SEQ": "td_seq",
    # Multi output
    "BB": "bbands",
    "MACD": "macd",
    "ADX": "adx",
    "DMI": "dm",
    "ATR": "atr",
    "NATR": "natr",
    "TRUE_RANGE": "true_range",
    "OBV": "obv",
    "MFI": "mfi",
    "CMF": "cmf",
    "AD": "ad",
    "ADOSC": "adosc",
    "EFI": "efi",
    "EMV": "emv",
    "EOM": "eom",
    "KVO": "kvo",
    "PVT": "pvt",
    "PVOL": "pvol",
    "PVR": "pvr",
    "VFI": "vfi",
    "VOSC": "vosc",
    "NVI": "nvi",
    "PVI": "pvi",
    "WAD": "wad",
    "MARKETFI": "marketfi",
    "VWAP": "vwap",
    "STOCH": "stoch",
    "STOCHF": "stochf",
    "STOCHRSI": "stochrsi",
    "KDJ": "kdj",
    "ICHIMOKU": "ichimoku",
    "SUPERTREND": "supertrend",
    "PSAR": "psar",
    "AROON": "aroon",
    "KC": "kc",
    "DONCHIAN": "donchian",
    "ACCBANDS": "accbands",
    "SQUEEZE": "squeeze",
    "SQUEEZE_PRO": "squeeze_pro",
    "AMAT": "amat",
    "MASSI": "massi",
    "THERMO": "thermo",
    "UI": "ui",
    "ENTROPY": "entropy",
    "MAD": "mad",
    "MEDIAN": "median",
    "QUANTILE": "quantile",
    "VARIANCE": "variance",
    "SKEW": "skew",
    "KURTOSIS": "kurtosis",
    "STDEV": "stdev",
    "ZSCORE": "zscore",
    "ABERRATION": "aberration",
    "HWC": "hwc",
    "HWMA": "hwma",
    "SSF": "ssf",
    "HILO": "hilo",
    "HA": "ha",
    "RMA": "rma",
    "MCGD": "mcgd",
    "PMAX": "pmax",
    "VORTEX": "vortex",
    "RVGI": "rvgi",
    "RVI": "rvi",
    "CVI": "cvi",
    "KST": "kst",
    "STDERR": "stderr",
    "TSF": "tsf",
    "BOP": "bop",
    "AVGPRICE": "avgprice",
    "WCP": "wcp",
    "MEDPRICE": "medprice",
    "TYPPRICE": "typprice",
    "HLC3": "hlc3",
    "HL2": "hl2",
    "OHLC4": "ohlc4",
    "MIDPOINT": "midpoint",
    "MIDPRICE": "midprice",
    "DECAY": "decay",
    "EDECAY": "edecay",
    "INCREASING": "increasing",
    "DECREASING": "decreasing",
    "SIGNED_SERIES": "signed_series",
    "CDL_PATTERN": "cdl_pattern",
}

# Category normalization: Excel Categories -> dim_indicator.Category
CATEGORY_MAP = {
    "Momentum": "MOMENTUM",
    "Volatility": "VOLATILITY",
    "Trend": "TREND",
    "Volume": "VOLUME",
    "Support": "STRUCTURE",
    "Mean Reversion": "MEAN_REVERSION",
    "Market": "MARKET_BREADTH",
    "Pattern": "PATTERN",
    "Cycle": "CYCLE",
    "Smoothing": "TREND",
    "Price": "PRICE",
    "Macro": "MACRO",
    "AI-generated": "CUSTOM",
}

# Alias mapping: IndicatorCode derived from Excel (no ShortName) -> registry key.
ALIAS_REGISTRY: dict[str, str] = {
    "STOCHASTIC_OSCILLATOR": "stoch",
    "ICHIMOKU_CLOUD": "ichimoku",
    "ICHIMOKU_KINKO_HYO": "ichimoku",
    "STANDARD_DEVIATION": "stdev",
    "AROON_OSCILLATOR": "aroon",
    "CHOPPINESS_INDEX": "chop",
    "ULTIMATE_OSCILLATOR": "uo",
    "RAINBOW_OSCILLATOR": "rainbow",
    "MOVING_AVERAGE_ENVELOPE": None,
    "FISHER_TRANSFORM": "fisher",
    "BOLLINGER_BANDS_WIDTH": None,
    "CUMULATIVE_RSI": None,
    "DISPARITY_INDEX": None,
    "KST_OSCILLATOR": "kst",
    "LINEAR_REGRESSION_INDICATOR": "linreg",
    "VOLUME_OSCILLATOR": "vosc",
    "WEIGHTED_CLOSE": "wcp",
    "ERGODIC_OSCILLATOR": "tsi",
    "WILLIAMS_VIXFIX": None,
    "ZERO_LAG_MACD": None,
    "ELDER_IMPULSE_SYSTEM": None,
    "EXPONENTIAL_MOVING_AVERAGE_RIBBON": None,
    "ELDER_FORCE_INDEX": "efi",
    "ATRP": "natr",
    "MOVING_AVERAGE_RIBBON": None,
    "RAINBOW_MOVING_AVERAGE": None,
    "ACCUMULATION_DISTRIBUTION_LINE": "ad",
    "KAUFMAN_ER": "er",
    "FDI": None,
    "RSC": None,
    "SWING_INDEX": None,
    "ASI": None,
    "CHANDELIER_EXIT_STOP": None,
    "CHANDE_KROLL_STOP": "cksp",
    "DYNAMIC_ZONE_RSI": None,
    "HURST_EXPONENT": None,
    "PROJECTION_BANDS": None,
    "RAFF_REGRESSION_CHANNEL": None,
    "RMI": None,
    "VAP": None,
    "VZO": None,
    "LARRY_WILLIAMS_VOLATILITY_CHANNEL": None,
    "DEMARKER_INDICATOR": None,
    "FRACTAL_INDICATOR": None,
    "MASS_INDEX": "massi",
    "ADAPTIVE_CYBER_CYCLE": None,
    "KALMAN_FILTER": None,
    "SUPERTREND_INDICATOR": "supertrend",
    "MCCLELLAN_OSCILLATOR": None,
    "QSTICK_INDICATOR": "qstick",
    "KLINGER_OSCILLATOR": "kvo",
    "PUT_CALL_RATIO": None,
    "TDI": None,
    "VORTEX_INDICATOR": "vortex",
    "ZWEIG_BREADTH_THRUST": None,
    "SAHM_RECESSION_INDICATOR": None,
    "DAVID_VARADI_OSCILLATOR": None,
    "DMA": None,
    "GAUSSIAN_FILTER": "ssf",
    "KAIRI_RELATIVE_INDEX": None,
    "JOHN_EHLERS_TRENDLINE": None,
    "JANUARY_BAROLLER": None,
    "JANUARY_BAROMETER": None,
    "KELTNER_CHANNELS": "kc",
    "MARKET_THRUST_INDICATOR": None,
    "ZERO_LAG_HULL_MOVING_AVERAGE": "hma",
    "ALEXANDER_ELDER_TRIPLE_SCREEN": None,
    "LINEAR_REGRESSION_SLOPE": "linregslope",
    "REX_OSCILLATOR": None,
    "STOCHASTIC_RSI": "stochrsi",
    "CHATGPT_INDICATOR": None,
    "CENTER_OF_GRAVITY_OSCILLATOR": "cg",
    "DOW_THEORY": None,
    "GATOR_OSCILLATOR": None,
    "LAGUERRE_RSI": "lrsi",
    "VOLUME_RSI": None,
    "CIDI": None,
    "BENNER_CYCLE": None,
    "ACCELERATION_BANDS": "accbands",
    "TIME_SERIES_ANALYSIS": None,
    "TSV": None,
    "ZIGZAG_FIBONACCI": None,
    "HIGH_LOW_BANDS": None,
    "PRIME_NUMBER_BANDS": None,
    "ADAPTIVE_LAGUERRE_FILTER": None,
    "TWIGGS_MONEY_FLOW": None,
    "WAVE_VOLUME": None,
    "ZERO_LAG_STOCHASTICS": None,
    "CMO_ABSOLUTE_INDICATOR": None,
    "FRACTAL_CHAOS_BANDS": None,
    "STARC": None,
    "MARKET_PROFILE": None,
    "STANDARD_ERROR_BANDS": "stderr",
    "WILLIAMS_ACCUMULATION_DISTRIBUTION": None,
    "PFE": None,
    "REI": None,
    "VROC": "roc",
    "MFI_BILL": None,
    "CONNORS_RSI": None,
}

def _normalize_code(short_name: str | float, indicator_name: str) -> str:
    """Derive a stable IndicatorCode from ShortName or indicator name."""
    base = short_name if isinstance(short_name, str) and short_name.strip() else indicator_name
    code = "".join(ch if ch.isalnum() else "_" for ch in base.strip().upper())
    while "__" in code:
        code = code.replace("__", "_")
    return code.strip("_")


def build_indicator_rows() -> tuple[pd.DataFrame, list[dict]]:
    """Build seed rows from Excel; return (rows_df, skipped_rows)."""
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    required_cols = {"Categories", "indicator", "ShortName", "Desc"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Excel thiếu các cột bắt buộc: {sorted(missing)}")

    rows: list[dict] = []
    skipped: list[dict] = []

    for _, row in df.iterrows():
        indicator_name = str(row["indicator"]).strip()
        category_raw = str(row["Categories"]).strip()
        desc = row["Desc"] if pd.notna(row["Desc"]) else None

        code = _normalize_code(row["ShortName"], indicator_name)
        if not code:
            skipped.append({"code": "", "name": indicator_name, "reason": "empty code"})
            continue

        function_name = INDICATOR_REGISTRY.get(code)
        if function_name is None and code in ALIAS_REGISTRY:
            function_name = ALIAS_REGISTRY[code]
        elif function_name is None:
            function_name = ALIAS_REGISTRY.get(code)
        if function_name is None or not hasattr(ta, function_name):
            skipped.append(
                {
                    "code": code,
                    "name": indicator_name,
                    "reason": f"no pandas-ta-classic mapping (registry={function_name})",
                }
            )
            continue

        rows.append(
            {
                "IndicatorCode": code,
                "IndicatorName": indicator_name,
                "Category": CATEGORY_MAP.get(category_raw, category_raw.upper()),
                "Engine": "PANDAS_TA_CLASSIC",
                "FunctionName": function_name,
                "RequiredInputs": json.dumps(["Close"]),
                "ParameterSchema": None,
                "Description": desc,
                "IsActive": True,
            }
        )

    # Deduplicate by IndicatorCode keeping first occurrence
    rows_df = pd.DataFrame(rows).drop_duplicates(subset=["IndicatorCode"], keep="first")
    return rows_df, skipped


def upsert_dim_indicator(rows_df: pd.DataFrame) -> int:
    """Upsert rows into dim_indicator; returns number of rows written."""
    if rows_df.empty:
        raise ValueError("Không có dòng nào để upsert vào dim_indicator.")

    con = DuckDBManager.get_connection(read_only=False)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS "CherryMon"."main"."dim_indicator" (
                IndicatorCode       VARCHAR NOT NULL,
                IndicatorName       VARCHAR NOT NULL,
                Category            VARCHAR NOT NULL,
                Engine              VARCHAR NOT NULL,
                FunctionName        VARCHAR NOT NULL,
                RequiredInputs      JSON NOT NULL,
                ParameterSchema     JSON,
                Description         VARCHAR,
                IsActive            BOOLEAN NOT NULL DEFAULT TRUE,
                CreatedAt           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt           TIMESTAMP,
                PRIMARY KEY (IndicatorCode)
            )
            """
        )

        con.register("df_indicator_seed", rows_df)

        before_count = con.execute(
            f'SELECT COUNT(*) FROM {TARGET_TABLE}'
        ).fetchone()[0]

        con.execute(
            f"""
            INSERT INTO {TARGET_TABLE} (
                IndicatorCode, IndicatorName, Category, Engine, FunctionName,
                RequiredInputs, ParameterSchema, Description, IsActive,
                CreatedAt, UpdatedAt
            )
            SELECT
                IndicatorCode, IndicatorName, Category, Engine, FunctionName,
                RequiredInputs, ParameterSchema, Description, IsActive,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM df_indicator_seed
            WHERE IndicatorCode NOT IN (
                SELECT IndicatorCode FROM {TARGET_TABLE}
            )
            """
        )

        # DuckDB has no changes() function; report update as executed without row count.
        updated_count = 0
        con.execute(
            f"""
            UPDATE {TARGET_TABLE}
            SET
                IndicatorName = s.IndicatorName,
                Category = s.Category,
                Engine = s.Engine,
                FunctionName = s.FunctionName,
                RequiredInputs = s.RequiredInputs,
                ParameterSchema = s.ParameterSchema,
                Description = s.Description,
                IsActive = s.IsActive,
                UpdatedAt = CURRENT_TIMESTAMP
            FROM df_indicator_seed s
            WHERE {TARGET_TABLE}.IndicatorCode = s.IndicatorCode
              AND ({TARGET_TABLE}.IndicatorName IS DISTINCT FROM s.IndicatorName
                   OR {TARGET_TABLE}.Category IS DISTINCT FROM s.Category
                   OR {TARGET_TABLE}.Engine IS DISTINCT FROM s.Engine
                   OR {TARGET_TABLE}.FunctionName IS DISTINCT FROM s.FunctionName
                   OR {TARGET_TABLE}.RequiredInputs IS DISTINCT FROM s.RequiredInputs
                   OR {TARGET_TABLE}.ParameterSchema IS DISTINCT FROM s.ParameterSchema
                   OR {TARGET_TABLE}.Description IS DISTINCT FROM s.Description
                   OR {TARGET_TABLE}.IsActive IS DISTINCT FROM s.IsActive)
            """
        )

        after_count = con.execute(
            f'SELECT COUNT(*) FROM {TARGET_TABLE}'
        ).fetchone()[0]
        inserted = after_count - before_count

        con.unregister("df_indicator_seed")
        con.commit()

        print(f"[seed_dim_indicator] inserted={inserted}, updated={updated_count}, total={after_count}")
        return after_count
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        DuckDBManager.close_connection(con)


def main() -> int:
    print(f"[seed_dim_indicator] start | excel={EXCEL_PATH}")
    rows_df, skipped = build_indicator_rows()
    print(f"[seed_dim_indicator] mapped rows: {len(rows_df)}, skipped: {len(skipped)}")

    if skipped:
        print("[seed_dim_indicator] skipped indicators:")
        for item in skipped:
            print(f"  - {item['code'] or '(no code)'} | {item['name']} | {item['reason']}")

    total = upsert_dim_indicator(rows_df)
    print(f"[seed_dim_indicator] success | dim_indicator total rows: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
