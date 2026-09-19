"""Diag: dump ZigZag V2 regime evaluation summary + swing-lock audit samples."""
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from cherrystock.config.settings import settings  # noqa: E402

con = duckdb.connect(settings.local_db_path, read_only=True)

summary = con.execute(
    """
    SELECT
        Ticker,
        BaseDeviationPct,
        StaticSwingCount,
        RegimeSwingCount,
        StaticShortSwingRate,
        RegimeShortSwingRate,
        StaticStructuralValid,
        RegimeStructuralValid,
        StaticScore,
        RegimeScore,
        LowVolBars,
        NormalBars,
        HighVolBars
    FROM "CherryMon"."main"."vw_ZigZag_Regime_Evaluation"
    WHERE RegimeVersion = 'V2.0'
    ORDER BY Ticker
    """
).df()
print(f"=== V2.0 regime summary: {len(summary)} rows ===")
print(summary.to_string(index=False))

# Idempotency row count
counts = con.execute(
    """
    SELECT RegimeVersion, COUNT(*) AS RowCount
    FROM "CherryMon"."main"."cal_zigzag_regime_evaluation"
    WHERE RegimeVersion = 'V2.0'
    GROUP BY RegimeVersion
    """
).df()
print("\n=== Idempotency counts ===")
print(counts.to_string(index=False))

# Swing-lock audit: deviation must be selected at previous pivot confirmation
audit = con.execute(
    """
    WITH ev AS (
        SELECT Ticker, PivotSeq, PivotType, PivotDate, PivotPrice,
               ConfirmedAtDate, DeviationPctUsed, DeviationSelectedAtDate, RegimeUsed
        FROM "CherryMon"."main"."cal_zigzag_regime_evaluation"
        WHERE RegimeVersion = 'V2.0' AND Ticker = 'MWG'
    )
    SELECT a.PivotSeq, a.PivotType, a.PivotDate, a.DeviationPctUsed,
           a.DeviationSelectedAtDate, b.ConfirmedAtDate AS PrevConfirmedAt,
           (a.DeviationSelectedAtDate = b.ConfirmedAtDate) AS LockOk,
           a.RegimeUsed
    FROM ev a
    LEFT JOIN ev b ON b.PivotSeq = a.PivotSeq - 1
    ORDER BY a.PivotSeq
    """
).df()
print("\n=== MWG swing-lock audit (all pivots) ===")
print("Total pivots:", len(audit))
print("LockOk violations (pivot>1):", int((audit.iloc[1:]["LockOk"] == False).sum()))
print("DeviationPctUsed range:", audit["DeviationPctUsed"].min(), "-", audit["DeviationPctUsed"].max())
print("First pivot RegimeUsed:", audit.iloc[0]["RegimeUsed"])
print(audit.head(8).to_string(index=False))
con.close()
