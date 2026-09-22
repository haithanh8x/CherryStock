from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readYahooFinance import _normalize_yf_eod  # noqa: E402
from cherrystock.application.services.yahoo_eod_diagnostic import (  # noqa: E402
    DEFAULT_PRECISION_TOLERANCE_BPS,
    YahooRawOtherEodDiagnostic,
    classify_ohlc_rows,
)
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


def _refetch_yahoo(
    invalid: pd.DataFrame,
    *,
    precision_tolerance_bps: float,
) -> pd.DataFrame:
    import yfinance as yf

    records: list[dict[str, object]] = []
    if invalid.empty:
        return pd.DataFrame()

    for row in invalid.itertuples(index=False):
        target = pd.Timestamp(row.Date).date()
        end = target + timedelta(days=1)
        ticker = str(row.Ticker)

        raw = yf.download(
            ticker,
            start=target.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        normalized = _normalize_yf_eod(raw, ticker)
        provider = normalized.loc[
            pd.to_datetime(normalized["Date"], errors="coerce").dt.date == target
        ]

        base = {
            "Ticker": ticker,
            "Date": target.isoformat(),
            "DbOpen": row.Open,
            "DbHigh": row.High,
            "DbLow": row.Low,
            "DbClose": row.Close,
            "DbRuleFlags": row.RuleFlags,
            "DbMaxViolationBps": row.MaxViolationBps,
        }

        if provider.empty:
            records.append(
                {
                    **base,
                    "ProviderStatus": "NO_PROVIDER_ROW",
                    "ProviderComparison": "PROVIDER_UNAVAILABLE",
                }
            )
            continue

        provider_row = provider.iloc[-1]
        provider_frame = classify_ohlc_rows(
            pd.DataFrame(
                [
                    {
                        "Ticker": ticker,
                        "Date": target,
                        "Open": provider_row["Open"],
                        "High": provider_row["High"],
                        "Low": provider_row["Low"],
                        "Close": provider_row["Close"],
                        "Volume": provider_row.get("Volume"),
                    }
                ]
            ),
            precision_tolerance_bps=precision_tolerance_bps,
        )
        classified = provider_frame.iloc[0]

        db_values = pd.Series([row.Open, row.High, row.Low, row.Close], dtype="float64")
        provider_values = pd.Series(
            [
                provider_row["Open"],
                provider_row["High"],
                provider_row["Low"],
                provider_row["Close"],
            ],
            dtype="float64",
        )
        max_abs_delta = float((db_values - provider_values).abs().max())
        scale = max(float(provider_values.abs().max()), 1e-12)
        max_delta_bps = max_abs_delta / scale * 10000.0

        if bool(classified["InvalidOHLC"]):
            comparison = "SOURCE_YAHOO_CANDIDATE"
        elif max_delta_bps > precision_tolerance_bps:
            comparison = "DB_DIFFERS_PROVIDER"
        else:
            comparison = "PROVIDER_NOW_VALID_DB_NEAR_MATCH"

        records.append(
            {
                **base,
                "ProviderStatus": "ROW_FOUND",
                "ProviderOpen": provider_row["Open"],
                "ProviderHigh": provider_row["High"],
                "ProviderLow": provider_row["Low"],
                "ProviderClose": provider_row["Close"],
                "ProviderInvalidOHLC": bool(classified["InvalidOHLC"]),
                "ProviderRuleFlags": classified["RuleFlags"],
                "ProviderMaxViolationBps": classified["MaxViolationBps"],
                "MaxDbProviderDeltaAbs": max_abs_delta,
                "MaxDbProviderDeltaBps": max_delta_bps,
                "ProviderComparison": comparison,
            }
        )

    return pd.DataFrame(records)


def _export(
    *,
    result: dict[str, object],
    evidence_dir: Path,
    provider_compare: pd.DataFrame | None,
) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)

    (evidence_dir / "Yahoo_Raw_Other_EOD_Diagnostic_Summary.json").write_text(
        json.dumps(result["summary"], indent=2, default=str),
        encoding="utf-8",
    )
    result["classified"].to_csv(
        evidence_dir / "Yahoo_Raw_Other_EOD_Target_Date.csv",
        index=False,
    )
    result["invalid"].to_csv(
        evidence_dir / "Yahoo_Raw_Other_EOD_Invalid_Rows.csv",
        index=False,
    )
    result["context"].to_csv(
        evidence_dir / "Yahoo_Raw_Other_EOD_Context.csv",
        index=False,
    )
    result["audit"].to_csv(
        evidence_dir / "Yahoo_Raw_Other_EOD_Audit.csv",
        index=False,
    )
    if provider_compare is not None:
        provider_compare.to_csv(
            evidence_dir / "Yahoo_Raw_Other_EOD_Provider_Compare.csv",
            index=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only diagnostic for Yahoo Finance raw_other_eod OHLC envelope failures."
        )
    )
    parser.add_argument(
        "--ticker",
        action="append",
        dest="tickers",
        help="Optional ticker from YAHOO_OTHER_TICKERS; repeat for multiple.",
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        help="Optional YYYY-MM-DD. Default: latest date in Yahoo diagnostic scope.",
    )
    parser.add_argument(
        "--context-rows",
        type=int,
        default=3,
        help="Previous/next database rows to include around each invalid row.",
    )
    parser.add_argument(
        "--precision-tolerance-bps",
        type=float,
        default=DEFAULT_PRECISION_TOLERANCE_BPS,
        help=(
            "Diagnostic-only threshold for labeling tiny envelope violations. "
            "Does not change DataValidation rules."
        ),
    )
    parser.add_argument(
        "--refetch-yahoo",
        action="store_true",
        help="Refetch only invalid ticker/date rows from Yahoo for source-vs-DB comparison.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Optional directory for diagnostic CSV/JSON evidence.",
    )
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="Return exit code 0 even when invalid OHLC rows are found.",
    )
    args = parser.parse_args()

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    diagnostic = YahooRawOtherEodDiagnostic(connection_factory=factory)
    result = diagnostic.run(
        requested_tickers=args.tickers,
        target_date=args.target_date,
        context_rows=args.context_rows,
        precision_tolerance_bps=args.precision_tolerance_bps,
    )

    summary = result["summary"]
    print("=== Yahoo raw_other_eod OHLC Diagnostic ===")
    for key, value in summary.items():
        print(f"{key}: {value}")

    invalid = result["invalid"]
    if not invalid.empty:
        print("\n--- Invalid OHLC row(s) ---")
        columns = [
            "Ticker",
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "RuleFlags",
            "MaxViolationAbs",
            "MaxViolationBps",
            "DiagnosticClass",
        ]
        print(invalid[columns].to_string(index=False))

    if not result["context"].empty:
        print("\n--- Neighboring DB context ---")
        print(result["context"].to_string(index=False))

    if not result["audit"].empty:
        print("\n--- Latest Yahoo Finance EOD DQ audit ---")
        print(result["audit"].head(3).to_string(index=False))

    provider_compare: pd.DataFrame | None = None
    if args.refetch_yahoo and not invalid.empty:
        print("\n--- Refetch Yahoo comparison ---")
        provider_compare = _refetch_yahoo(
            invalid,
            precision_tolerance_bps=args.precision_tolerance_bps,
        )
        if provider_compare.empty:
            print("No provider comparison rows.")
        else:
            print(provider_compare.to_string(index=False))

    if args.evidence_dir is not None:
        _export(
            result=result,
            evidence_dir=args.evidence_dir,
            provider_compare=provider_compare,
        )
        print(f"\nevidence_dir: {args.evidence_dir}")

    invalid_count = int(summary["invalid_ohlc_count"])
    if invalid_count == 0:
        print("\nDIAGNOSTIC RESULT: CLEAN")
        return 0

    precision_count = int(summary["precision_candidate_count"])
    material_count = int(summary["material_violation_count"])
    if material_count > 0:
        print(
            "\nDIAGNOSTIC RESULT: INVALID_OHLC — material envelope violation candidate. "
            "Use --refetch-yahoo before deciding whether to resync or change validation."
        )
    elif precision_count > 0:
        print(
            "\nDIAGNOSTIC RESULT: INVALID_OHLC — tiny floating-point candidate only. "
            "Use --refetch-yahoo; do not change DQ tolerance without separate validation."
        )

    return 0 if args.allow_invalid else 2


if __name__ == "__main__":
    raise SystemExit(main())
