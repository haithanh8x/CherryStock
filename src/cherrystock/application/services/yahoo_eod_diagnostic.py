from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

import pandas as pd

from CrawlStock.readYahooFinance import YAHOO_OTHER_TICKERS


RAW_OTHER_EOD = '"CherryMon"."main"."raw_other_eod"'
DQ_AUDIT = '"CherryMon"."main"."sys_data_quality_audit"'
YAHOO_PIPELINE = "Yahoo Finance EOD"
DEFAULT_PRECISION_TOLERANCE_BPS = 0.01

_RULE_COLUMNS = (
    ("HIGH_LT_LOW", "HighLtLow"),
    ("HIGH_LT_OPEN", "HighLtOpen"),
    ("HIGH_LT_CLOSE", "HighLtClose"),
    ("LOW_GT_OPEN", "LowGtOpen"),
    ("LOW_GT_CLOSE", "LowGtClose"),
)


def _normalize_date(value: date | datetime | str | pd.Timestamp | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("target_date must use YYYY-MM-DD")
    return parsed.date()


def normalize_tickers(values: Iterable[str] | None = None) -> list[str]:
    allowed = [str(value).strip() for value in YAHOO_OTHER_TICKERS if str(value).strip()]
    if values is None:
        return allowed

    requested = []
    for value in values:
        ticker = str(value).strip()
        if ticker and ticker not in requested:
            requested.append(ticker)

    unknown = sorted(set(requested).difference(allowed))
    if unknown:
        raise ValueError(
            "Requested ticker(s) are outside YAHOO_OTHER_TICKERS: "
            + ", ".join(unknown)
        )
    if not requested:
        raise ValueError("ticker selection must not be empty")
    return requested


def classify_ohlc_rows(
    frame: pd.DataFrame,
    *,
    precision_tolerance_bps: float = DEFAULT_PRECISION_TOLERANCE_BPS,
) -> pd.DataFrame:
    """Replicate the generic DataValidation OHLC envelope rule and explain each row."""

    if precision_tolerance_bps < 0:
        raise ValueError("precision_tolerance_bps must be >= 0")

    required = ["Ticker", "Date", "Open", "High", "Low", "Close"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing required diagnostic column(s): {missing}")

    result = frame.copy()
    for column in ("Open", "High", "Low", "Close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result["HighLtLow"] = result["High"] < result["Low"]
    result["HighLtOpen"] = result["High"] < result["Open"]
    result["HighLtClose"] = result["High"] < result["Close"]
    result["LowGtOpen"] = result["Low"] > result["Open"]
    result["LowGtClose"] = result["Low"] > result["Close"]
    result["InvalidOHLC"] = result[
        [column for _, column in _RULE_COLUMNS]
    ].any(axis=1)

    violations = pd.DataFrame(
        {
            "HIGH_LT_LOW": (result["Low"] - result["High"]).clip(lower=0),
            "HIGH_LT_OPEN": (result["Open"] - result["High"]).clip(lower=0),
            "HIGH_LT_CLOSE": (result["Close"] - result["High"]).clip(lower=0),
            "LOW_GT_OPEN": (result["Low"] - result["Open"]).clip(lower=0),
            "LOW_GT_CLOSE": (result["Low"] - result["Close"]).clip(lower=0),
        },
        index=result.index,
    )
    result["MaxViolationAbs"] = violations.max(axis=1, skipna=True).fillna(0.0)

    price_scale = result[["Open", "High", "Low", "Close"]].abs().max(axis=1)
    result["PriceScale"] = price_scale
    result["MaxViolationBps"] = (
        result["MaxViolationAbs"]
        / price_scale.where(price_scale > 0)
        * 10000.0
    ).fillna(0.0)

    def _flags(row: pd.Series) -> str:
        return "|".join(
            name for name, column in _RULE_COLUMNS if bool(row[column])
        )

    result["RuleFlags"] = result.apply(_flags, axis=1)
    result["DiagnosticClass"] = "CLEAN"
    precision_candidate = (
        result["InvalidOHLC"]
        & (result["MaxViolationBps"] <= float(precision_tolerance_bps))
    )
    material = result["InvalidOHLC"] & ~precision_candidate
    result.loc[precision_candidate, "DiagnosticClass"] = "FLOAT_PRECISION_CANDIDATE"
    result.loc[material, "DiagnosticClass"] = "MATERIAL_OHLC_ENVELOPE_VIOLATION"

    return result


class YahooRawOtherEodDiagnostic:
    """Read-only diagnostic for Yahoo raw_other_eod Data Quality failures."""

    def __init__(self, *, connection_factory) -> None:
        self._factory = connection_factory

    def _resolve_target_date(
        self,
        connection,
        *,
        tickers: list[str],
        target_date: date | datetime | str | pd.Timestamp | None,
    ) -> date:
        explicit = _normalize_date(target_date)
        if explicit is not None:
            return explicit

        placeholders = ", ".join("?" for _ in tickers)
        row = connection.execute(
            f"""
            SELECT MAX(Date)
            FROM {RAW_OTHER_EOD}
            WHERE Ticker IN ({placeholders})
            """,
            tickers,
        ).fetchone()
        if row is None or row[0] is None:
            raise RuntimeError(
                "Unable to resolve latest Yahoo raw_other_eod date for diagnostic scope."
            )
        return pd.Timestamp(row[0]).date()

    def _latest_audit(self, connection, *, limit: int = 5) -> pd.DataFrame:
        try:
            return connection.execute(
                f"""
                SELECT
                    validation_id,
                    checked_at,
                    pipeline_name,
                    table_name,
                    expected_date,
                    max_date,
                    status,
                    row_count_current,
                    symbol_count_current,
                    duplicate_count,
                    CAST(metrics AS VARCHAR) AS metrics,
                    CAST(errors AS VARCHAR) AS errors,
                    CAST(warnings AS VARCHAR) AS warnings
                FROM {DQ_AUDIT}
                WHERE pipeline_name = ?
                  AND lower(table_name) LIKE '%raw_other_eod%'
                ORDER BY checked_at DESC
                LIMIT ?
                """,
                [YAHOO_PIPELINE, int(limit)],
            ).df()
        except Exception:
            # Audit history is supporting evidence only. The raw-table diagnosis must still work
            # on older/local databases without the audit table.
            return pd.DataFrame()

    def _context(
        self,
        connection,
        *,
        tickers: list[str],
        target_date: date,
        context_rows: int,
    ) -> pd.DataFrame:
        if not tickers:
            return pd.DataFrame()
        placeholders = ", ".join("?" for _ in tickers)
        return connection.execute(
            f"""
            WITH ordered AS (
                SELECT
                    Ticker,
                    Date,
                    Open,
                    High,
                    Low,
                    Close,
                    Volume,
                    ROW_NUMBER() OVER (
                        PARTITION BY Ticker
                        ORDER BY Date
                    ) AS rn
                FROM {RAW_OTHER_EOD}
                WHERE Ticker IN ({placeholders})
            ),
            target AS (
                SELECT Ticker, rn AS target_rn
                FROM ordered
                WHERE Date = ?
            )
            SELECT
                o.Ticker,
                o.Date,
                o.Open,
                o.High,
                o.Low,
                o.Close,
                o.Volume,
                CAST(o.rn - t.target_rn AS INTEGER) AS RelativeRow
            FROM ordered AS o
            JOIN target AS t
              ON t.Ticker = o.Ticker
            WHERE o.rn BETWEEN t.target_rn - ? AND t.target_rn + ?
            ORDER BY o.Ticker, o.Date
            """,
            [*tickers, target_date, int(context_rows), int(context_rows)],
        ).df()

    def run(
        self,
        *,
        requested_tickers: Iterable[str] | None = None,
        target_date: date | datetime | str | pd.Timestamp | None = None,
        context_rows: int = 3,
        precision_tolerance_bps: float = DEFAULT_PRECISION_TOLERANCE_BPS,
    ) -> dict[str, object]:
        if context_rows < 0:
            raise ValueError("context_rows must be >= 0")

        tickers = normalize_tickers(requested_tickers)

        with self._factory.reader() as connection:
            resolved_date = self._resolve_target_date(
                connection,
                tickers=tickers,
                target_date=target_date,
            )
            placeholders = ", ".join("?" for _ in tickers)
            daily = connection.execute(
                f"""
                SELECT
                    Ticker,
                    Date,
                    Open,
                    High,
                    Low,
                    Close,
                    Volume
                FROM {RAW_OTHER_EOD}
                WHERE Ticker IN ({placeholders})
                  AND Date = ?
                ORDER BY Ticker
                """,
                [*tickers, resolved_date],
            ).df()

            classified = classify_ohlc_rows(
                daily,
                precision_tolerance_bps=precision_tolerance_bps,
            )
            invalid = classified.loc[classified["InvalidOHLC"]].copy()
            invalid_tickers = invalid["Ticker"].astype(str).tolist()
            context = self._context(
                connection,
                tickers=invalid_tickers,
                target_date=resolved_date,
                context_rows=context_rows,
            )
            audit = self._latest_audit(connection)

        summary = {
            "target_date": resolved_date.isoformat(),
            "scope_tickers": tickers,
            "scope_ticker_count": len(tickers),
            "rows_on_target_date": int(len(classified)),
            "invalid_ohlc_count": int(classified["InvalidOHLC"].sum()),
            "precision_candidate_count": int(
                (classified["DiagnosticClass"] == "FLOAT_PRECISION_CANDIDATE").sum()
            ),
            "material_violation_count": int(
                (
                    classified["DiagnosticClass"]
                    == "MATERIAL_OHLC_ENVELOPE_VIOLATION"
                ).sum()
            ),
            "max_violation_abs": (
                0.0
                if invalid.empty
                else float(invalid["MaxViolationAbs"].max())
            ),
            "max_violation_bps": (
                0.0
                if invalid.empty
                else float(invalid["MaxViolationBps"].max())
            ),
            "precision_tolerance_bps": float(precision_tolerance_bps),
        }

        return {
            "summary": summary,
            "classified": classified,
            "invalid": invalid,
            "context": context,
            "audit": audit,
        }
