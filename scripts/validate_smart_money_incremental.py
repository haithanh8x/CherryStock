from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from calcEngine.smartMoneyScore import refresh_smart_money_score  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.repositories.smart_money_repository import (  # noqa: E402
    SmartMoneyRepository,
)


def _ticker_clause(tickers: list[str]) -> tuple[str, list[object]]:
    placeholders = ", ".join("?" for _ in tickers)
    return f"({placeholders})", list(tickers)


def _load_scores(connection, tickers: list[str], start_date) -> pd.DataFrame:
    clause, params = _ticker_clause(tickers)
    return connection.execute(
        f"""
        SELECT
            ModelId,
            Ticker,
            Date,
            SmartMoneyScore,
            ConfidenceScore,
            MarketState,
            FactorCoverage,
            DataQualityStatus
        FROM "CherryMon"."main"."cal_smart_money_ticker_score"
        WHERE Ticker IN {clause}
          AND Date >= ?
        ORDER BY ModelId, Ticker, Date
        """,
        [*params, start_date],
    ).df()


def _load_factors(connection, tickers: list[str], start_date) -> pd.DataFrame:
    clause, params = _ticker_clause(tickers)
    return connection.execute(
        f"""
        SELECT
            ModelId,
            Ticker,
            Date,
            FactorId,
            RawValue,
            NormalizedValue,
            DataQuality,
            SourceCode
        FROM "CherryMon"."main"."cal_smart_money_factor_values"
        WHERE Ticker IN {clause}
          AND Date >= ?
        ORDER BY ModelId, Ticker, Date, FactorId
        """,
        [*params, start_date],
    ).df()


def _assert_equal(before: pd.DataFrame, after: pd.DataFrame, label: str) -> None:
    if before.empty:
        raise RuntimeError(f"{label} baseline is empty; run full SmartMoney initload first.")
    pd.testing.assert_frame_equal(
        before.reset_index(drop=True),
        after.reset_index(drop=True),
        check_dtype=False,
        check_exact=False,
        rtol=1e-10,
        atol=1e-10,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate full-history vs incremental SmartMoney convergence with rollback."
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["MWG", "FPT", "HPG"],
    )
    args = parser.parse_args()

    tickers = sorted({value.strip().upper() for value in args.tickers if value.strip()})
    if not tickers:
        raise ValueError("At least one ticker is required.")

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    connection = factory.create_writer()
    connection.execute("BEGIN")
    try:
        max_date = connection.execute(
            """
            SELECT MAX(Date)
            FROM "CherryMon"."main"."cal_smart_money_ticker_score"
            """
        ).fetchone()[0]
        if max_date is None:
            raise RuntimeError("No SmartMoney baseline; run full historical initload first.")

        start_date = pd.Timestamp(max_date).date() - pd.Timedelta(days=int(args.days))
        start_date = pd.Timestamp(start_date).date()

        before_scores = _load_scores(connection, tickers, start_date)
        before_factors = _load_factors(connection, tickers, start_date)

        summary = refresh_smart_money_score(
            from_last_day=int(args.days),
            tickers=tickers,
            connection=connection,
            repository=SmartMoneyRepository(connection),
        )
        after_scores = _load_scores(connection, tickers, start_date)
        after_factors = _load_factors(connection, tickers, start_date)

        _assert_equal(before_scores, after_scores, "score")
        _assert_equal(before_factors, after_factors, "factor")

        print("SmartMoney full/incremental convergence: PASS")
        print("Tickers:", tickers)
        print("Start date:", start_date)
        print("Score rows:", len(after_scores))
        print("Factor rows:", len(after_factors))
        print("Incremental summary:", summary)
        return 0
    finally:
        connection.execute("ROLLBACK")
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
