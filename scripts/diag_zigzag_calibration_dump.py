"""Diag: inspect ZigZag V1.1 calibration grid + recommendations."""
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from cherrystock.config.settings import settings  # noqa: E402

con = duckdb.connect(settings.local_db_path, read_only=True)

version = sys.argv[1] if len(sys.argv) > 1 else "V1.1"

grid = con.execute(
    f"""
    SELECT
        SplitName,
        DeviationPct,
        SwingCount,
        PivotDensityPer100Bars,
        MedianSwingBars,
        MedianAbsSwingPct,
        ShortSwingRate,
        StructuralValid,
        IsEligible,
        CalibrationScore
    FROM "CherryMon"."main"."vw_ZigZag_Calibration"
    WHERE CalibrationVersion = '{version}'
    ORDER BY Ticker,
        CASE SplitName WHEN 'TRAIN' THEN 1 WHEN 'VALIDATION' THEN 2 ELSE 3 END,
        DeviationPct
    """
).df()
print(f"=== Calibration grid {version}: {len(grid)} rows ===")
print(grid.to_string(index=False))

recs = con.execute(
    f"""
    SELECT
        CalibrationVersion,
        Ticker,
        BaseDeviationPct,
        SelectionMethod,
        TrainScore,
        ValidationScore,
        TestScore,
        Status,
        IsActive
    FROM "CherryMon"."main"."vw_ZigZag_Ticker_Config"
    WHERE CalibrationVersion = '{version}'
    ORDER BY Ticker
    """
).df()
print(f"\n=== Recommendations {version}: {len(recs)} rows ===")
print(recs.to_string(index=False))

pilot = con.execute(
    f"""
    SELECT PilotVersion, COUNT(*) AS RowCount
    FROM "CherryMon"."main"."cal_zigzag_pilot_evaluation"
    WHERE PilotVersion = '{version}'
    GROUP BY PilotVersion
    """
).df()
print(f"\n=== Pilot evaluation rows ===")
print(pilot.to_string(index=False))

pilot_detail = con.execute(
    f"""
    SELECT
        Ticker,
        BaselineDeviationPct,
        CalibratedDeviationPct,
        BaselineShortSwingRate,
        CalibratedShortSwingRate,
        BaselineScore,
        CalibratedScore,
        BaselineStructuralValid,
        CalibratedStructuralValid,
        Decision
    FROM "CherryMon"."main"."cal_zigzag_pilot_evaluation"
    WHERE PilotVersion = '{version}'
    ORDER BY Ticker
    """
).df()
print(f"\n=== Pilot decisions {version} ===")
print(pilot_detail.to_string(index=False))
con.close()
