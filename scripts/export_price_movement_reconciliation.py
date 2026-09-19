from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import DuckDBConnectionFactory  # noqa: E402


DEFAULT_TICKER = "MWG"
DEFAULT_PM_CONFIG_CODE = "PM_ZZ_D_V2"


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected YYYY-MM-DD."
        ) from exc


def _output_dir(ticker: str) -> Path:
    return (
        settings.project_root
        / "docs"
        / "reference"
        / "data"
        / "price_movement"
        / ticker.lower()
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def _count_identity_mismatches(
    zigzag: pd.DataFrame,
    movement: pd.DataFrame,
) -> dict[str, int]:
    if zigzag.empty and movement.empty:
        return {
            "MissingMovementSwingCount": 0,
            "ExtraMovementSwingCount": 0,
            "IdentityMismatchCount": 0,
            "NumericMismatchCount": 0,
        }

    left = zigzag.rename(
        columns={
            "ConfigId": "ZigZagConfigId",
            "ConfigCode": "ZigZagConfigCode",
        }
    )
    merged = left.merge(
        movement,
        on=["ZigZagConfigId", "ZigZagConfigCode", "Ticker", "SwingSeq"],
        how="outer",
        suffixes=("_zz", "_pm"),
        indicator=True,
    )

    missing = int((merged["_merge"] == "left_only").sum())
    extra = int((merged["_merge"] == "right_only").sum())

    matched = merged.loc[merged["_merge"] == "both"].copy()
    identity_mismatch = 0
    numeric_mismatch = 0

    for row in matched.itertuples(index=False):
        exact_pairs = (
            ("Direction_zz", "Direction_pm"),
            ("StartPivotSeq_zz", "StartPivotSeq_pm"),
            ("EndPivotSeq_zz", "EndPivotSeq_pm"),
            ("StartDate_zz", "StartDate_pm"),
            ("EndDate_zz", "EndDate_pm"),
            ("ConfirmedAtDate_zz", "ConfirmedAtDate_pm"),
        )
        if any(getattr(row, a) != getattr(row, b) for a, b in exact_pairs):
            identity_mismatch += 1

        numeric_pairs = (
            ("StartPrice_zz", "StartPrice_pm"),
            ("EndPrice_zz", "EndPrice_pm"),
            ("SwingPct_zz", "SwingPct_pm"),
        )
        if any(
            not np.isclose(
                float(getattr(row, a)),
                float(getattr(row, b)),
                rtol=1e-9,
                atol=1e-9,
            )
            for a, b in numeric_pairs
        ):
            numeric_mismatch += 1

    return {
        "MissingMovementSwingCount": missing,
        "ExtraMovementSwingCount": extra,
        "IdentityMismatchCount": identity_mismatch,
        "NumericMismatchCount": numeric_mismatch,
    }


def _movement_formula_mismatches(
    movement: pd.DataFrame,
    ohlc: pd.DataFrame,
) -> dict[str, int]:
    if movement.empty:
        return {
            "SwingPctFormulaMismatchCount": 0,
            "TradingBarsMismatchCount": 0,
            "VelocityMismatchCount": 0,
            "PathEfficiencyBoundsViolationCount": 0,
            "PersistenceBoundsViolationCount": 0,
            "PointInTimeViolationCount": 0,
        }

    swing_pct_mismatch = 0
    trading_bars_mismatch = 0
    velocity_mismatch = 0

    ohlc_dates = pd.to_datetime(ohlc["Date"])

    for row in movement.itertuples(index=False):
        expected_swing_pct = float(row.EndPrice) / float(row.StartPrice) - 1.0
        if not np.isclose(
            float(row.SwingPct),
            expected_swing_pct,
            rtol=1e-9,
            atol=1e-9,
        ):
            swing_pct_mismatch += 1

        start = pd.Timestamp(row.StartDate)
        end = pd.Timestamp(row.EndDate)
        expected_bars = int(((ohlc_dates >= start) & (ohlc_dates <= end)).sum() - 1)
        if int(row.TradingBars) != expected_bars:
            trading_bars_mismatch += 1

        expected_velocity = expected_swing_pct / int(row.TradingBars)
        if not np.isclose(
            float(row.VelocityPctPerBar),
            expected_velocity,
            rtol=1e-9,
            atol=1e-9,
        ):
            velocity_mismatch += 1

    efficiency_violations = int(
        (
            (movement["PathEfficiency"] < 0)
            | (movement["PathEfficiency"] > 1)
        ).sum()
    )
    persistence_violations = int(
        (
            (movement["DirectionalPersistenceRate"] < 0)
            | (movement["DirectionalPersistenceRate"] > 1)
        ).sum()
    )
    point_in_time_violations = int(
        (
            pd.to_datetime(movement["EndDate"])
            >= pd.to_datetime(movement["ConfirmedAtDate"])
        ).sum()
    )

    return {
        "SwingPctFormulaMismatchCount": swing_pct_mismatch,
        "TradingBarsMismatchCount": trading_bars_mismatch,
        "VelocityMismatchCount": velocity_mismatch,
        "PathEfficiencyBoundsViolationCount": efficiency_violations,
        "PersistenceBoundsViolationCount": persistence_violations,
        "PointInTimeViolationCount": point_in_time_violations,
    }


def export_reconciliation_package(
    *,
    ticker: str,
    pm_config_code: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    ticker = ticker.strip().upper()
    pm_config_code = pm_config_code.strip()
    if not ticker:
        raise ValueError("ticker must not be empty.")
    if not pm_config_code:
        raise ValueError("pm_config_code must not be empty.")

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)

    with factory.reader() as connection:
        config = connection.execute(
            """
            SELECT
                ConfigId,
                ConfigCode,
                ModelVersion,
                Timeframe,
                ZigZagConfigCode,
                ProfileLookbackSwings,
                MinimumProfileSwings,
                TrendBiasThreshold,
                RangeBiasThreshold,
                EfficiencyThreshold,
                ATRPeriod,
                IsEnabled
            FROM "CherryMon"."main"."dim_price_movement_config"
            WHERE ConfigCode = ?
            LIMIT 1
            """,
            [pm_config_code],
        ).df()

        if config.empty:
            raise RuntimeError(
                f"Price Movement config '{pm_config_code}' was not found."
            )

        cfg = config.iloc[0]
        zigzag_config_code = str(cfg["ZigZagConfigCode"])
        lookback = int(cfg["ProfileLookbackSwings"])
        atr_period = int(cfg["ATRPeriod"])

        profile = connection.execute(
            """
            SELECT
                PriceMovementConfigCode,
                PriceMovementModelVersion,
                Timeframe,
                PriceMovementConfigId,
                ZigZagConfigId,
                ZigZagConfigCode,
                Ticker,
                AsOfConfirmedAtDate,
                ProfileLookbackSwings,
                ConfirmedSwingCount,
                LastSwingSeq,
                LastSwingDirection,
                LastSwingPct,
                MedianUpSwingPct,
                MedianDownSwingAbsPct,
                MedianAbsSwingPct,
                MedianTradingBars,
                MedianAbsVelocityPctPerBar,
                MedianATRNormalizedMove,
                MedianPathEfficiency,
                MedianDirectionalPersistenceRate,
                DirectionalBias,
                MovementCharacter
            FROM "CherryMon"."main"."vw_Ticker_Movement_Profile"
            WHERE Ticker = ?
              AND PriceMovementConfigCode = ?
            """,
            [ticker, pm_config_code],
        ).df()

        if profile.empty:
            raise RuntimeError(
                f"No Price Movement profile for {ticker}/{pm_config_code}. "
                "Run the Price Movement initload first."
            )

        all_movement = connection.execute(
            """
            SELECT
                PriceMovementConfigId,
                ZigZagConfigId,
                ZigZagConfigCode,
                Ticker,
                SwingSeq,
                Direction,
                StartPivotSeq,
                StartDate,
                StartPrice,
                EndPivotSeq,
                EndDate,
                EndPrice,
                ConfirmedAtDate,
                SwingPct,
                TradingBars,
                CalendarDays,
                VelocityPctPerBar,
                AvgATR20Pct,
                ATRNormalizedMove,
                PathEfficiency,
                DirectionalPersistenceRate
            FROM "CherryMon"."main"."vw_Ticker_Price_Movement_Swings"
            WHERE Ticker = ?
              AND PriceMovementConfigCode = ?
            ORDER BY SwingSeq
            """,
            [ticker, pm_config_code],
        ).df()

        if all_movement.empty:
            raise RuntimeError(
                f"No Price Movement swings for {ticker}/{pm_config_code}."
            )

        recent = all_movement.tail(lookback).copy()
        default_start = pd.to_datetime(recent["StartDate"]).min().date()
        default_end = pd.to_datetime(recent["EndDate"]).max().date()

        core_start = start_date or default_start
        core_end = end_date or default_end
        if core_start > core_end:
            raise ValueError("start_date must be <= end_date.")

        movement = all_movement.loc[
            (pd.to_datetime(all_movement["EndDate"]).dt.date >= core_start)
            & (pd.to_datetime(all_movement["StartDate"]).dt.date <= core_end)
        ].copy()

        zigzag = connection.execute(
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
            [ticker, zigzag_config_code, core_start, core_end],
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
            [ticker, zigzag_config_code, core_start, core_end],
        ).df()

        warmup_days = max(60, atr_period * 3)
        ohlc_start = core_start - timedelta(days=warmup_days)
        profile_as_of = pd.Timestamp(
            profile.iloc[0]["AsOfConfirmedAtDate"]
        ).date()
        ohlc_end = max(core_end, profile_as_of)

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
            [ticker, ohlc_start, ohlc_end],
        ).df()

    for frame in (movement, zigzag, pivots, profile, ohlc):
        for column in (
            "Date",
            "StartDate",
            "EndDate",
            "PivotDate",
            "ConfirmedAtDate",
            "AsOfConfirmedAtDate",
        ):
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column])

    identity = _count_identity_mismatches(zigzag, movement)
    formulas = _movement_formula_mismatches(movement, ohlc)

    profile_last_seq_mismatch = 0
    profile_asof_mismatch = 0
    if len(profile) != 1:
        profile_last_seq_mismatch = 1
        profile_asof_mismatch = 1
    else:
        recent_all = all_movement.tail(lookback)
        expected_last_seq = int(recent_all.iloc[-1]["SwingSeq"])
        actual_last_seq = int(profile.iloc[0]["LastSwingSeq"])
        profile_last_seq_mismatch = int(expected_last_seq != actual_last_seq)

        expected_asof = pd.Timestamp(
            pd.to_datetime(recent_all["ConfirmedAtDate"]).max()
        )
        actual_asof = pd.Timestamp(profile.iloc[0]["AsOfConfirmedAtDate"])
        profile_asof_mismatch = int(expected_asof != actual_asof)

    check_values = {
        **identity,
        **formulas,
        "ProfileLastSwingMismatchCount": profile_last_seq_mismatch,
        "ProfileAsOfMismatchCount": profile_asof_mismatch,
    }
    total_errors = int(sum(check_values.values()))
    status = "PASS" if total_errors == 0 else "FAIL"

    summary_items: list[tuple[str, object]] = [
        ("Ticker", ticker),
        ("PriceMovementConfigCode", pm_config_code),
        ("ZigZagConfigCode", zigzag_config_code),
        ("CoreStartDate", core_start),
        ("CoreEndDate", core_end),
        ("OHLCWarmupStartDate", ohlc_start),
        ("ProfileAsOfConfirmedAtDate", profile_as_of),
        ("ZigZagSwingRows", len(zigzag)),
        ("PriceMovementSwingRows", len(movement)),
        ("ZigZagPivotRows", len(pivots)),
        ("OHLCRows", len(ohlc)),
        ("ProfileRows", len(profile)),
    ]
    summary_items.extend(check_values.items())
    summary_items.extend(
        [
            ("TotalCoreErrors", total_errors),
            ("ReconciliationStatus", status),
        ]
    )
    summary = pd.DataFrame(summary_items, columns=["Metric", "Value"])

    target_dir = _output_dir(ticker)
    start_token = core_start.strftime("%Y%m%d")
    end_token = core_end.strftime("%Y%m%d")

    files = {
        "config": target_dir / f"{ticker}_Price_Movement_Config.csv",
        "ohlc": target_dir / f"{ticker}_OHLC_{start_token}_{end_token}_with_warmup.csv",
        "pivots": target_dir / f"{ticker}_ZigZag_Pivots_{start_token}_{end_token}.csv",
        "zigzag_swings": target_dir / f"{ticker}_ZigZag_Swings_{start_token}_{end_token}.csv",
        "movement_swings": target_dir / f"{ticker}_Price_Movement_Swings_{start_token}_{end_token}.csv",
        "profile": target_dir / f"{ticker}_Movement_Profile.csv",
        "summary": target_dir / f"{ticker}_Price_Movement_Reconciliation_Summary.csv",
    }

    _write_csv(config, files["config"])
    _write_csv(ohlc, files["ohlc"])
    _write_csv(pivots, files["pivots"])
    _write_csv(zigzag, files["zigzag_swings"])
    _write_csv(movement, files["movement_swings"])
    _write_csv(profile, files["profile"])
    _write_csv(summary, files["summary"])

    return {
        "ticker": ticker,
        "pm_config_code": pm_config_code,
        "zigzag_config_code": zigzag_config_code,
        "core_start_date": core_start,
        "core_end_date": core_end,
        "output_dir": target_dir,
        "reconciliation_status": status,
        "total_core_errors": total_errors,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export Price Movement V2 reconciliation evidence for ChatGPT review."
        )
    )
    parser.add_argument("--ticker", default=DEFAULT_TICKER)
    parser.add_argument("--pm-config-code", default=DEFAULT_PM_CONFIG_CODE)
    parser.add_argument("--start-date", type=_parse_date)
    parser.add_argument("--end-date", type=_parse_date)
    args = parser.parse_args()

    result = export_reconciliation_package(
        ticker=args.ticker,
        pm_config_code=args.pm_config_code,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    print("=== Price Movement V2 reconciliation export ===")
    for key in (
        "ticker",
        "pm_config_code",
        "zigzag_config_code",
        "core_start_date",
        "core_end_date",
        "output_dir",
        "reconciliation_status",
        "total_core_errors",
    ):
        print(f"{key}: {result[key]}")

    print("\nFiles:")
    for name, path in result["files"].items():
        print(f"  {name}: {path}")

    print(
        "\nNext: git add docs/reference/data/price_movement/"
        f"{result['ticker'].lower()}/"
    )
    return 0 if result["reconciliation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
