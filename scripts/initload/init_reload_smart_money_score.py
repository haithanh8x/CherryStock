from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Ults import DuckLib  # noqa: E402
from Ults.DuckLib import executeDuckSQL  # noqa: E402
from calcEngine.smartMoneyScore import refresh_smart_money_score  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402
from cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork  # noqa: E402


SCHEMA_SQL = PROJECT_ROOT / "src" / "DuckDB" / "sql" / "smart_money_v1_schema.sql"

HISTORICAL_VALIDATION_SQL = """
WITH enabled_scores AS (
    SELECT
        s.ModelId,
        s.Ticker,
        s.Date
    FROM "CherryMon"."main"."cal_smart_money_ticker_score" AS s
    INNER JOIN "CherryMon"."main"."dim_smart_money_model" AS m
        ON m.ModelId = s.ModelId
    WHERE m.IsEnabled = TRUE
      AND s.Date >= m.EffectiveFrom
      AND (m.EffectiveTo IS NULL OR s.Date <= m.EffectiveTo)
),
score_stats AS (
    SELECT
        COUNT(*) AS ScoreRows,
        MIN(Date) AS ScoreMinDate,
        MAX(Date) AS ScoreMaxDate
    FROM enabled_scores
),
view_stats AS (
    SELECT
        COUNT(*) AS ViewRows,
        MIN(Date) AS ViewMinDate,
        MAX(Date) AS ViewMaxDate,
        COALESCE(SUM(CASE
            WHEN TradeActionConfidenceScore IS NULL
              OR TradeActionConfidenceScore < 0
              OR TradeActionConfidenceScore > 100
            THEN 1 ELSE 0
        END), 0) AS InvalidRange,
        COALESCE(SUM(CASE
            WHEN TradeActionConfidenceScore > ConfidenceScore + 0.000001
            THEN 1 ELSE 0
        END), 0) AS AboveUpstreamConfidence,
        COALESCE(SUM(CASE
            WHEN DataQualityStatus <> 'PASS'
             AND ABS(TradeActionConfidenceScore) > 0.000001
            THEN 1 ELSE 0
        END), 0) AS NonPassConfidenceMismatch,
        COALESCE(SUM(CASE
            WHEN TradeAction IS NULL
              OR TradeAction NOT IN ('BUY', 'HOLD', 'SELL')
            THEN 1 ELSE 0
        END), 0) AS InvalidTradeAction
    FROM "CherryMon"."main"."vw_Ticker_SmartMoney"
)
SELECT
    s.ScoreRows,
    v.ViewRows,
    s.ScoreMinDate,
    s.ScoreMaxDate,
    v.ViewMinDate,
    v.ViewMaxDate,
    v.InvalidRange,
    v.AboveUpstreamConfidence,
    v.NonPassConfidenceMismatch,
    v.InvalidTradeAction
FROM score_stats AS s
CROSS JOIN view_stats AS v
"""


def validate_historical_public_contract(connection) -> dict[str, object]:
    """Validate full historical public-view coverage and action-confidence invariants."""
    row = connection.execute(HISTORICAL_VALIDATION_SQL).fetchone()
    if row is None:
        raise RuntimeError("SmartMoney historical validation returned no result.")

    validation = {
        "score_rows": int(row[0] or 0),
        "view_rows": int(row[1] or 0),
        "score_min_date": row[2],
        "score_max_date": row[3],
        "view_min_date": row[4],
        "view_max_date": row[5],
        "invalid_range": int(row[6] or 0),
        "above_upstream_confidence": int(row[7] or 0),
        "non_pass_confidence_mismatch": int(row[8] or 0),
        "invalid_trade_action": int(row[9] or 0),
    }

    failures: list[str] = []
    if validation["score_rows"] <= 0:
        failures.append("no enabled historical SmartMoney score rows")
    if validation["view_rows"] != validation["score_rows"]:
        failures.append(
            "public-view historical row count does not match enabled persisted score rows"
        )
    if validation["view_min_date"] != validation["score_min_date"]:
        failures.append("public-view historical start date does not match persisted scores")
    if validation["view_max_date"] != validation["score_max_date"]:
        failures.append("public-view historical end date does not match persisted scores")
    if validation["invalid_range"] != 0:
        failures.append("TradeActionConfidenceScore contains NULL/out-of-range values")
    if validation["above_upstream_confidence"] != 0:
        failures.append("TradeActionConfidenceScore exceeds ConfidenceScore")
    if validation["non_pass_confidence_mismatch"] != 0:
        failures.append("non-PASS rows contain non-zero TradeActionConfidenceScore")
    if validation["invalid_trade_action"] != 0:
        failures.append("TradeAction contains NULL/unsupported values")

    if failures:
        raise RuntimeError(
            "SmartMoney historical public contract validation failed: "
            + "; ".join(failures)
            + f". Evidence: {validation}"
        )

    return validation


def main() -> int:
    """Bootstrap SmartMoney V1 and perform full historical backfill + contract validation."""
    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with DuckDBUnitOfWork(factory) as uow:
        if uow.connection is None or uow.smart_money is None:
            raise RuntimeError("UnitOfWork did not initialize SmartMoney dependencies.")

        executeDuckSQL(
            con=uow.connection,
            sql_file_path=str(SCHEMA_SQL),
            sql_description="SmartMoney V1 schema + metadata seed",
        )
        summary = refresh_smart_money_score(
            from_last_day=None,
            tickers=None,
            model_ids=None,
            connection=uow.connection,
            repository=uow.smart_money,
        )
        if int(summary.get("score_rows_upserted", 0)) <= 0:
            raise RuntimeError(f"SmartMoney full historical initload produced no score rows: {summary}")

        validation = validate_historical_public_contract(uow.connection)
        print("SmartMoney full historical summary:", summary)
        print("SmartMoney historical public-contract validation:", validation)

    DuckLib.exportDuckDB_metadata()
    print(
        "SmartMoney V1 full historical initload committed; "
        "TradeActionConfidenceScore historical contract validated; DB metadata exported."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
