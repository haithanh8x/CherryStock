from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


DEFAULT_TICKER = "MWG"
DEFAULT_CONFIG_CODE = "ZZ_D_5_MVP"
DEFAULT_START_DATE = date(2026, 5, 1)
DEFAULT_END_DATE = date(2026, 9, 30)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected YYYY-MM-DD."
        ) from exc


def _date_token(value: date) -> str:
    return value.strftime("%Y%m%d")


def _output_dir(ticker: str) -> Path:
    return (
        settings.project_root
        / "docs"
        / "reference"
        / "data"
        / "zigzag"
        / ticker.lower()
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def export_reconciliation_package(
    *,
    ticker: str,
    config_code: str,
    start_date: date,
    end_date: date,
) -> dict[str, object]:
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date.")

    ticker = ticker.strip().upper()
    config_code = config_code.strip()
    if not ticker:
        raise ValueError("ticker must not be empty.")
    if not config_code:
        raise ValueError("config_code must not be empty.")

    target_dir = _output_dir(ticker)
    start_token = _date_token(start_date)
    end_token = _date_token(end_date)

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        config = connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                DeviationPct,
                PivotPriceSource,
                ConfirmationPriceSource,
                MinimumSwingBars
            FROM "CherryMon"."main"."dim_zigzag_config"
            WHERE ConfigCode = ?
            LIMIT 1
            """,
            [config_code],
        ).fetchone()
        if config is None:
            raise RuntimeError(
                f"ZigZag config '{config_code}' was not found. "
                "Run the ZigZag MWG initload first."
            )

        ohlc = connection.execute(
            """
            SELECT
                Ticker,
                Date,
                Open,
                High,
                Low,
                Close,
                Volume,
                TradingValue,
                TradingValue_Source,
                TradingValue_IsProxy
            FROM "CherryMon"."main"."vw_Ticker_OHLC_D"
            WHERE Ticker = ?
              AND Date BETWEEN ? AND ?
            ORDER BY Date
            """,
            [ticker, start_date, end_date],
        ).df()

        pivots = connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                DeviationPct,
                Ticker,
                PivotSeq,
                PivotType,
                PivotDate,
                PivotPrice,
                ConfirmedAtDate,
                ConfirmationPrice
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Pivots"
            WHERE Ticker = ?
              AND ConfigCode = ?
              AND PivotDate BETWEEN ? AND ?
            ORDER BY PivotSeq
            """,
            [ticker, config_code, start_date, end_date],
        ).df()

        swings = connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                DeviationPct,
                Ticker,
                SwingSeq,
                Direction,
                StartPivotSeq,
                StartPivotType,
                StartDate,
                StartPrice,
                EndPivotSeq,
                EndPivotType,
                EndDate,
                EndPrice,
                ConfirmedAtDate,
                SwingPct,
                CalendarDays
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Swings"
            WHERE Ticker = ?
              AND ConfigCode = ?
              AND EndDate >= ?
              AND StartDate <= ?
            ORDER BY SwingSeq
            """,
            [ticker, config_code, start_date, end_date],
        ).df()

        reconciliation = connection.execute(
            """
            SELECT
                o.Ticker,
                o.Date,
                o.Open,
                o.High,
                o.Low,
                o.Close,
                o.Volume,
                o.TradingValue,
                p.ConfigCode,
                p.ModelVersion,
                p.DeviationPct,
                p.PivotSeq,
                p.PivotType,
                p.PivotPrice,
                p.ConfirmedAtDate,
                p.ConfirmationPrice,
                CASE
                    WHEN p.PivotType = 'LOW' THEN p.PivotPrice
                    ELSE NULL
                END AS ZigZagLow,
                CASE
                    WHEN p.PivotType = 'HIGH' THEN p.PivotPrice
                    ELSE NULL
                END AS ZigZagHigh,
                CASE
                    WHEN p.PivotSeq IS NOT NULL THEN TRUE
                    ELSE FALSE
                END AS IsConfirmedPivot
            FROM "CherryMon"."main"."vw_Ticker_OHLC_D" AS o
            LEFT JOIN "CherryMon"."main"."vw_Ticker_ZigZag_Pivots" AS p
              ON p.Ticker = o.Ticker
             AND p.PivotDate = o.Date
             AND p.ConfigCode = ?
            WHERE o.Ticker = ?
              AND o.Date BETWEEN ? AND ?
            ORDER BY o.Date
            """,
            [config_code, ticker, start_date, end_date],
        ).df()

        current = connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                DeviationPct,
                Ticker,
                AsOfDate,
                Direction,
                StartPivotSeq,
                StartPivotDate,
                StartPivotPrice,
                CandidatePivotType,
                CandidatePivotDate,
                CandidatePivotPrice,
                LastClose,
                CurrentMovePct,
                ReversalFromCandidatePct,
                Status
            FROM "CherryMon"."main"."vw_Ticker_ZigZag_Current"
            WHERE Ticker = ?
              AND ConfigCode = ?
            """,
            [ticker, config_code],
        ).df()

    if ohlc.empty:
        raise RuntimeError(
            f"No OHLC rows found for {ticker} between {start_date} and {end_date}."
        )

    files = {
        "ohlc": target_dir / f"{ticker}_OHLC_{start_token}_{end_token}.csv",
        "pivots": target_dir / f"{ticker}_ZigZag_Pivots_{start_token}_{end_token}.csv",
        "swings": target_dir / f"{ticker}_ZigZag_Swings_{start_token}_{end_token}.csv",
        "reconciliation": target_dir
        / f"{ticker}_ZigZag_Reconciliation_{start_token}_{end_token}.csv",
        "current": target_dir / f"{ticker}_ZigZag_Current.csv",
    }

    _write_csv(ohlc, files["ohlc"])
    _write_csv(pivots, files["pivots"])
    _write_csv(swings, files["swings"])
    _write_csv(reconciliation, files["reconciliation"])
    _write_csv(current, files["current"])

    return {
        "ticker": ticker,
        "config_code": config_code,
        "config_id": int(config[0]),
        "model_version": str(config[2]),
        "deviation_pct": float(config[4]),
        "start_date": start_date,
        "end_date": end_date,
        "output_dir": target_dir,
        "ohlc_rows": len(ohlc),
        "pivot_rows": len(pivots),
        "swing_rows": len(swings),
        "reconciliation_rows": len(reconciliation),
        "current_rows": len(current),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export a bounded ZigZag reconciliation package for TradingView/ChatGPT review."
        )
    )
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    parser.add_argument("--config-code", default=DEFAULT_CONFIG_CODE)
    parser.add_argument(
        "--start-date",
        type=_parse_date,
        default=DEFAULT_START_DATE,
        help="Inclusive start date (YYYY-MM-DD). Default: 2026-05-01.",
    )
    parser.add_argument(
        "--end-date",
        type=_parse_date,
        default=DEFAULT_END_DATE,
        help="Inclusive end date (YYYY-MM-DD). Default: 2026-09-30.",
    )
    args = parser.parse_args()

    summary = export_reconciliation_package(
        ticker=args.ticker,
        config_code=args.config_code,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    print("=== ZigZag TradingView reconciliation export ===")
    for key in (
        "ticker",
        "config_code",
        "config_id",
        "model_version",
        "deviation_pct",
        "start_date",
        "end_date",
        "output_dir",
        "ohlc_rows",
        "pivot_rows",
        "swing_rows",
        "reconciliation_rows",
        "current_rows",
    ):
        print(f"{key}: {summary[key]}")

    print("\nFiles:")
    for name, path in summary["files"].items():
        print(f"  {name}: {path}")

    print(
        "\nNext: git add docs/reference/data/zigzag/"
        f"{summary['ticker'].lower()}/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
