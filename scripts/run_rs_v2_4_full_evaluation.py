"""Monthly full-universe R/S V2.4 Source Effectiveness orchestration.

This script coordinates the existing evaluation/effectiveness/promotion runners.
It does not duplicate R/S calculation logic and does not mutate runtime weights
or provider registration.

Default:
    python scripts/run_rs_v2_4_full_evaluation.py

Focused smoke:
    python scripts/run_rs_v2_4_full_evaluation.py ^
        --tickers MWG,FPT,HPG ^
        --horizons 20 ^
        --only-source-keys MA50_D ^
        --scopes SOURCE_CONFIG ^
        --plan-only

Monthly default behavior:
- eligible universe from raw_stock_eod;
- 3-year evaluation lookback;
- H5/H10/H20/H40;
- point-in-time-safe evaluation end with future bars reserved;
- SOURCE_CONFIG + SOURCE_FAMILY ablation;
- Source Promotion Gate dry-run;
- deterministic run ids and resumable completed child runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from calcEngine.levelLadder import (  # noqa: E402
    BB_LEVEL_COMPONENTS,
    SOURCE_FAMILY_MARKET_STRUCTURE,
    SOURCE_FAMILY_MOMENTUM_CONFIRMATION,
    SOURCE_FAMILY_TREND_AVERAGE,
    SOURCE_FAMILY_VOLATILITY_BAND,
    SOURCE_FAMILY_VOLATILITY_CONTEXT,
    SOURCE_FAMILY_VOLUME_STRUCTURE,
    SOURCE_ROLE_CONFIRMATION,
    SOURCE_ROLE_CONTEXT,
    SOURCE_ROLE_LEVEL,
    SUPPORTED_TIMEFRAMES,
)
from calcEngine.rsSourceIdentity import canonical_source_key  # noqa: E402
from cherrystock.config.settings import settings  # noqa: E402
from cherrystock.infrastructure.database.connection import (  # noqa: E402
    DuckDBConnectionFactory,
)

EVALUATION_SCRIPT = PROJECT_ROOT / "scripts" / "run_rs_v2_3_evaluation.py"
EFFECTIVENESS_SCRIPT = PROJECT_ROOT / "scripts" / "run_rs_v2_4_source_effectiveness.py"
PROMOTION_SCRIPT = PROJECT_ROOT / "scripts" / "promote_rs_v2_4_source.py"

CANONICAL_HORIZONS = (5, 10, 20, 40)
DEFAULT_LOOKBACK_YEARS = 3
DEFAULT_MIN_HISTORY_BARS = 500
DEFAULT_FRESHNESS_BARS = 5


@dataclass(frozen=True, order=True)
class SourceSpec:
    source_key: str
    source_family: str
    source_role: str


@dataclass(frozen=True)
class EvaluationWindow:
    start_date: date
    evaluation_end: date
    latest_data_date: date
    freshness_cutoff: date


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monthly R/S V2.4 full Source Effectiveness orchestration"
    )
    parser.add_argument(
        "--tickers",
        default="",
        help="Comma-separated ticker override. Default: eligible universe.",
    )
    parser.add_argument("--start", default=None, help="Evaluation start YYYY-MM-DD.")
    parser.add_argument(
        "--end",
        default=None,
        help=(
            "Evaluation end YYYY-MM-DD. Must leave enough future trading bars "
            "for the largest horizon. Default is resolved automatically."
        ),
    )
    parser.add_argument("--lookback-years", type=int, default=DEFAULT_LOOKBACK_YEARS)
    parser.add_argument(
        "--horizons",
        default=",".join(str(value) for value in CANONICAL_HORIZONS),
    )
    parser.add_argument("--snapshot-step", type=int, default=5)
    parser.add_argument("--min-history-bars", type=int, default=DEFAULT_MIN_HISTORY_BARS)
    parser.add_argument("--freshness-bars", type=int, default=DEFAULT_FRESHNESS_BARS)
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=None,
        help="Deterministic ticker cap for smoke/testing only.",
    )
    parser.add_argument(
        "--scopes",
        default="SOURCE_CONFIG,SOURCE_FAMILY",
        help="SOURCE_CONFIG,SOURCE_FAMILY or both.",
    )
    parser.add_argument(
        "--only-source-keys",
        default="",
        help="Optional canonical source keys to evaluate.",
    )
    parser.add_argument(
        "--skip-source-keys",
        default="",
        help="Optional canonical source keys to skip.",
    )
    parser.add_argument(
        "--extra-source-specs-json",
        default="[]",
        help=(
            "JSON list with source_key, source_family, source_role. "
            "Use only for already-integrated/observable sources."
        ),
    )
    parser.add_argument("--effectiveness-policy-json", default="{}")
    parser.add_argument("--promotion-policy-json", default="{}")
    parser.add_argument(
        "--promotion-mode",
        choices=("dry-run", "audit", "skip"),
        default="dry-run",
        help="Default dry-run. audit persists governance metadata only.",
    )
    parser.add_argument("--run-month", default=None, help="YYYY-MM monthly label.")
    parser.add_argument("--run-prefix", default=None)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse compatible COMPLETED child runs.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Resolve date/universe/baseline plan without executing child jobs.",
    )
    return parser.parse_args()


def _parse_csv(raw: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                part.strip().upper()
                for part in str(raw or "").split(",")
                if part.strip()
            }
        )
    )


def _parse_horizons(raw: str) -> tuple[int, ...]:
    try:
        values = tuple(
            sorted({int(part.strip()) for part in raw.split(",") if part.strip()})
        )
    except ValueError as exc:
        raise ValueError("--horizons must be comma-separated positive integers") from exc
    if not values or any(value <= 0 for value in values):
        raise ValueError("--horizons must contain at least one positive integer")
    return values


def _parse_scopes(raw: str) -> tuple[str, ...]:
    scopes = _parse_csv(raw)
    allowed = {"SOURCE_CONFIG", "SOURCE_FAMILY"}
    invalid = set(scopes) - allowed
    if not scopes or invalid:
        raise ValueError(
            "--scopes must contain SOURCE_CONFIG and/or SOURCE_FAMILY; "
            f"invalid={sorted(invalid)}"
        )
    return scopes


def _parse_json_object(raw: str, name: str) -> dict:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must decode to a JSON object")
    return value


def _parse_extra_source_specs(raw: str) -> tuple[SourceSpec, ...]:
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("--extra-source-specs-json must decode to a JSON list")
    allowed_roles = {
        SOURCE_ROLE_LEVEL,
        SOURCE_ROLE_CONTEXT,
        SOURCE_ROLE_CONFIRMATION,
    }
    result: set[SourceSpec] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"extra source spec index={index} must be an object")
        missing = {"source_key", "source_family", "source_role"} - set(item)
        if missing:
            raise ValueError(
                f"extra source spec index={index} missing {sorted(missing)}"
            )
        role = str(item["source_role"]).strip().upper()
        if role not in allowed_roles:
            raise ValueError(
                f"extra source spec index={index} has invalid source_role={role}"
            )
        result.add(
            SourceSpec(
                canonical_source_key(str(item["source_key"])),
                str(item["source_family"]).strip().upper(),
                role,
            )
        )
    return tuple(sorted(result))


def _month_tag(raw: str | None) -> str:
    if raw is None:
        return date.today().strftime("%Y%m")
    if not re.fullmatch(r"\d{4}-\d{2}", raw):
        raise ValueError("--run-month must use YYYY-MM")
    year, month = (int(value) for value in raw.split("-"))
    if not 1 <= month <= 12:
        raise ValueError("--run-month month must be between 01 and 12")
    return f"{year:04d}{month:02d}"


def _slug(value: str, max_length: int = 40) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")
    if not normalized:
        raise ValueError("identifier cannot normalize to blank")
    return normalized[:max_length]


def _short_hash(values: Iterable[str]) -> str:
    payload = "|".join(sorted(str(value).upper() for value in values))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:8].upper()


def _ablation_model_version(
    scope_type: str,
    label: str,
    excluded_source_keys: Sequence[str],
) -> str:
    scope_code = "SRC" if scope_type == "SOURCE_CONFIG" else "FAM"
    return (
        f"RS_V2_4_ABL_{scope_code}_{_slug(label, 28)}_"
        f"{_short_hash(excluded_source_keys)}"
    )


def _build_run_prefix(
    explicit_prefix: str | None,
    month_tag: str,
    evaluation_end: date,
    tickers: Sequence[str],
    snapshot_step: int,
) -> str:
    if explicit_prefix:
        return _slug(explicit_prefix, 56)
    universe_hash = _short_hash(tickers)
    return (
        f"RSV24FULL_{month_tag}_E{evaluation_end:%Y%m%d}_"
        f"S{snapshot_step}_U{universe_hash}"
    )


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    return date.fromisoformat(str(value))


def _market_dates(connection) -> list[date]:
    rows = connection.execute(
        """
        SELECT DISTINCT "Date"
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE "Date" IS NOT NULL
        ORDER BY "Date";
        """
    ).fetchall()
    values = [_as_date(row[0]) for row in rows]
    if not values:
        raise RuntimeError("raw_stock_eod has no trading dates")
    return values


def _resolve_window(
    connection,
    horizons: Sequence[int],
    explicit_start: str | None,
    explicit_end: str | None,
    lookback_years: int,
    freshness_bars: int,
) -> EvaluationWindow:
    if lookback_years <= 0:
        raise ValueError("--lookback-years must be > 0")
    if freshness_bars < 0:
        raise ValueError("--freshness-bars must be >= 0")

    market_dates = _market_dates(connection)
    latest = market_dates[-1]
    max_horizon = max(horizons)

    if explicit_end:
        evaluation_end = date.fromisoformat(explicit_end)
        if evaluation_end > latest:
            raise ValueError("--end cannot be later than latest raw_stock_eod date")
        future_dates = [value for value in market_dates if evaluation_end < value <= latest]
        if len(future_dates) < max_horizon:
            raise ValueError(
                "--end leaves insufficient future trading bars: "
                f"required={max_horizon}, available={len(future_dates)}"
            )
    else:
        if len(market_dates) <= max_horizon:
            raise RuntimeError(
                f"Not enough trading dates to reserve horizon={max_horizon}"
            )
        evaluation_end = market_dates[-(max_horizon + 1)]

    start_date = (
        date.fromisoformat(explicit_start)
        if explicit_start
        else evaluation_end - timedelta(days=365 * lookback_years)
    )
    if start_date >= evaluation_end:
        raise ValueError("evaluation start must be earlier than evaluation end")

    freshness_index = max(0, len(market_dates) - 1 - freshness_bars)
    return EvaluationWindow(
        start_date=start_date,
        evaluation_end=evaluation_end,
        latest_data_date=latest,
        freshness_cutoff=market_dates[freshness_index],
    )


def _resolve_tickers(
    connection,
    window: EvaluationWindow,
    explicit_tickers: Sequence[str],
    min_history_bars: int,
    max_tickers: int | None,
) -> tuple[str, ...]:
    if min_history_bars <= 0:
        raise ValueError("--min-history-bars must be > 0")
    if max_tickers is not None and max_tickers <= 0:
        raise ValueError("--max-tickers must be > 0")

    rows = connection.execute(
        """
        SELECT
            "Ticker",
            COUNT(*) AS "BarCount",
            MIN("Date") AS "MinDate",
            MAX("Date") AS "MaxDate"
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE "Date" BETWEEN ? AND ?
        GROUP BY "Ticker"
        HAVING COUNT(*) >= ?
           AND MAX("Date") >= ?
        ORDER BY "Ticker";
        """,
        [
            window.start_date,
            window.latest_data_date,
            min_history_bars,
            window.freshness_cutoff,
        ],
    ).fetchall()
    eligible = {str(row[0]).upper() for row in rows}

    if explicit_tickers:
        requested = tuple(sorted(set(str(value).upper() for value in explicit_tickers)))
        ineligible = sorted(set(requested) - eligible)
        if ineligible:
            raise ValueError(
                "requested tickers fail history/freshness eligibility: "
                f"{ineligible}. Adjust --min-history-bars if intentional."
            )
        result = requested
    else:
        result = tuple(sorted(eligible))

    if max_tickers is not None:
        result = result[:max_tickers]
    if not result:
        raise RuntimeError("No eligible tickers resolved")
    return result


def _expected_snapshot_count(
    connection,
    tickers: Sequence[str],
    window: EvaluationWindow,
    snapshot_step: int,
) -> int:
    placeholders = ",".join("?" for _ in tickers)
    rows = connection.execute(
        f"""
        SELECT
            "Ticker",
            COUNT(*) AS "BarCount"
        FROM "CherryMon"."main"."raw_stock_eod"
        WHERE "Ticker" IN ({placeholders})
          AND "Date" BETWEEN ? AND ?
        GROUP BY "Ticker";
        """,
        [*tickers, window.start_date, window.evaluation_end],
    ).fetchall()
    counts = {str(row[0]).upper(): int(row[1]) for row in rows}
    missing = sorted(set(tickers) - set(counts))
    if missing:
        raise ValueError(f"snapshot-count source data missing tickers: {missing}")
    return sum((counts[ticker] + snapshot_step - 1) // snapshot_step for ticker in tickers)


def _indicator_source_specs(connection) -> set[SourceSpec]:
    rows = connection.execute(
        """
        SELECT
            "ConfigCode",
            "IndicatorCode",
            "Timeframe",
            "ComponentCode",
            "ValueSemantic"
        FROM "CherryMon"."main"."vw_Indicator_config"
        WHERE "IndicatorCode" IN ('MA', 'BB', 'ATR', 'RSI')
          AND "ConfigIsEnabled" = TRUE
          AND "IndicatorIsActive" = TRUE
          AND "ComponentIsActive" = TRUE
          AND "Timeframe" IN ('D', 'W', 'M')
        ORDER BY "IndicatorCode", "ConfigCode", "ComponentCode";
        """
    ).fetchall()

    result: set[SourceSpec] = set()
    for config_code, indicator_code, timeframe, component_code, value_semantic in rows:
        indicator = str(indicator_code).upper()
        timeframe_value = str(timeframe).upper()
        config = str(config_code).upper()
        component = str(component_code or "").upper()
        semantic = str(value_semantic or "").upper()

        if timeframe_value not in SUPPORTED_TIMEFRAMES:
            continue
        if indicator == "MA" and semantic == "PRICE_LEVEL":
            result.add(
                SourceSpec(
                    canonical_source_key(config),
                    SOURCE_FAMILY_TREND_AVERAGE,
                    SOURCE_ROLE_LEVEL,
                )
            )
        elif (
            indicator == "BB"
            and semantic == "PRICE_LEVEL"
            and component in set(BB_LEVEL_COMPONENTS)
        ):
            result.add(
                SourceSpec(
                    canonical_source_key(f"{config}:{component}"),
                    SOURCE_FAMILY_VOLATILITY_BAND,
                    SOURCE_ROLE_LEVEL,
                )
            )
        elif indicator == "ATR" and config == "ATR14_D":
            result.add(
                SourceSpec(
                    canonical_source_key(config),
                    SOURCE_FAMILY_VOLATILITY_CONTEXT,
                    SOURCE_ROLE_CONTEXT,
                )
            )
        elif indicator == "RSI" and config == "RSI14_D":
            result.add(
                SourceSpec(
                    canonical_source_key(config),
                    SOURCE_FAMILY_MOMENTUM_CONFIRMATION,
                    SOURCE_ROLE_CONFIRMATION,
                )
            )
    return result


def _static_source_specs() -> set[SourceSpec]:
    structural = {
        "SWING_HIGH",
        "SWING_LOW",
        "PREV_WEEK_HIGH",
        "PREV_WEEK_LOW",
        "PREV_MONTH_HIGH",
        "PREV_MONTH_LOW",
        "HIGH_52W",
        "LOW_52W",
    }
    result = {
        SourceSpec(key, SOURCE_FAMILY_MARKET_STRUCTURE, SOURCE_ROLE_LEVEL)
        for key in structural
    }
    result.update(
        {
            SourceSpec("VP_POC", SOURCE_FAMILY_VOLUME_STRUCTURE, SOURCE_ROLE_LEVEL),
            SourceSpec("VP_HVN", SOURCE_FAMILY_VOLUME_STRUCTURE, SOURCE_ROLE_LEVEL),
            SourceSpec("VP_LVN", SOURCE_FAMILY_VOLUME_STRUCTURE, SOURCE_ROLE_LEVEL),
        }
    )
    return result


def _baseline_lineage_keys(connection, baseline_run_id: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT "SourcesJson"
        FROM "CherryMon"."main"."cal_rs_evaluation_event"
        WHERE "EvaluationRunId" = ?
          AND "SourcesJson" IS NOT NULL;
        """,
        [baseline_run_id],
    ).fetchall()
    result: set[str] = set()
    for (raw_json,) in rows:
        for source_code in json.loads(raw_json or "[]"):
            result.add(canonical_source_key(str(source_code)))
    return result


def _discover_source_catalog(
    connection,
    baseline_run_id: str,
    extra_specs: Sequence[SourceSpec],
) -> tuple[tuple[SourceSpec, ...], set[str]]:
    catalog = _indicator_source_specs(connection) | _static_source_specs() | set(extra_specs)
    lineage = _baseline_lineage_keys(connection, baseline_run_id)
    if not catalog:
        raise RuntimeError("R/S source catalog is empty")
    return tuple(sorted(catalog)), lineage


def _select_config_specs(
    catalog: Sequence[SourceSpec],
    lineage: set[str],
    only_source_keys: Sequence[str],
    skip_source_keys: Sequence[str],
) -> tuple[SourceSpec, ...]:
    # LEVEL requires direct baseline lineage. CONTEXT/CONFIRMATION are marginal-only.
    selected = {
        spec
        for spec in catalog
        if spec.source_role != SOURCE_ROLE_LEVEL or spec.source_key in lineage
    }
    only = {canonical_source_key(value) for value in only_source_keys}
    skip = {canonical_source_key(value) for value in skip_source_keys}
    if only:
        selected = {spec for spec in selected if spec.source_key in only}
        missing = sorted(only - {spec.source_key for spec in selected})
        if missing:
            raise ValueError(
                "--only-source-keys not active/observable in baseline: "
                f"{missing}"
            )
    if skip:
        selected = {spec for spec in selected if spec.source_key not in skip}
    if not selected:
        raise RuntimeError("No source configs remain after selection")
    return tuple(sorted(selected))


def _family_groups(
    full_catalog: Sequence[SourceSpec],
    selected_specs: Sequence[SourceSpec],
) -> dict[tuple[str, str], tuple[str, ...]]:
    selected_families = {spec.source_family for spec in selected_specs}
    roles_by_family: dict[str, set[str]] = {}
    members: dict[tuple[str, str], set[str]] = {}

    for spec in full_catalog:
        if spec.source_family not in selected_families:
            continue
        roles_by_family.setdefault(spec.source_family, set()).add(spec.source_role)
        members.setdefault((spec.source_family, spec.source_role), set()).add(spec.source_key)

    mixed = {
        family: sorted(roles)
        for family, roles in roles_by_family.items()
        if len(roles) > 1
    }
    if mixed:
        raise ValueError(f"source family has mixed roles: {mixed}")

    return {
        key: tuple(sorted(values))
        for key, values in sorted(members.items())
        if values
    }


def _check_child_scripts() -> None:
    missing = [
        str(path.relative_to(PROJECT_ROOT))
        for path in (EVALUATION_SCRIPT, EFFECTIVENESS_SCRIPT, PROMOTION_SCRIPT)
        if not path.exists()
    ]
    if missing:
        raise RuntimeError(f"Required restored R/S runner(s) missing: {missing}")


def _evaluation_run_state(connection, run_id: str) -> dict | None:
    row = connection.execute(
        """
        SELECT
            "DatasetStart",
            "DatasetEnd",
            "HorizonBars",
            "TickerCount",
            "SnapshotCount",
            "Status",
            "IncludeSourceKeysJson",
            "ExcludeSourceKeysJson"
        FROM "CherryMon"."main"."cal_rs_evaluation_run"
        WHERE "EvaluationRunId" = ?;
        """,
        [run_id],
    ).fetchone()
    if row is None:
        return None
    ticker_rows = connection.execute(
        """
        SELECT DISTINCT "Ticker"
        FROM "CherryMon"."main"."cal_rs_evaluation_event"
        WHERE "EvaluationRunId" = ?
        ORDER BY "Ticker";
        """,
        [run_id],
    ).fetchall()
    return {
        "dataset_start": _as_date(row[0]),
        "dataset_end": _as_date(row[1]),
        "horizon_bars": int(row[2]),
        "ticker_count": int(row[3]),
        "snapshot_count": int(row[4]),
        "status": str(row[5]),
        "include_keys": tuple(sorted(json.loads(row[6] or "[]"))),
        "exclude_keys": tuple(sorted(json.loads(row[7] or "[]"))),
        "event_tickers": tuple(str(item[0]).upper() for item in ticker_rows),
    }


def _effectiveness_run_state(connection, run_id: str) -> dict | None:
    row = connection.execute(
        """
        SELECT
            "ScopeType",
            "SourceKey",
            "SourceFamily",
            "SourceRole",
            "HorizonBars",
            "BaselineRunId",
            "AblationRunId",
            "Status"
        FROM "CherryMon"."main"."cal_rs_source_effectiveness_run"
        WHERE "EffectivenessRunId" = ?;
        """,
        [run_id],
    ).fetchone()
    if row is None:
        return None
    return {
        "scope_type": str(row[0]),
        "source_key": str(row[1]),
        "source_family": str(row[2]),
        "source_role": str(row[3]),
        "horizon_bars": int(row[4]),
        "baseline_run_id": str(row[5]),
        "ablation_run_id": str(row[6]),
        "status": str(row[7]),
    }


def _assert_evaluation_compatible(
    state: dict,
    run_id: str,
    window: EvaluationWindow,
    horizon: int,
    excluded_source_keys: Sequence[str],
    tickers: Sequence[str],
    expected_snapshot_count: int,
) -> None:
    expected_excluded = tuple(
        sorted(canonical_source_key(value) for value in excluded_source_keys)
    )
    actual_excluded = tuple(
        sorted(canonical_source_key(value) for value in state["exclude_keys"])
    )
    mismatches: list[str] = []
    if state["dataset_start"] != window.start_date:
        mismatches.append("DatasetStart")
    if state["dataset_end"] != window.evaluation_end:
        mismatches.append("DatasetEnd")
    if state["horizon_bars"] != horizon:
        mismatches.append("HorizonBars")
    if state["ticker_count"] != len(tickers):
        mismatches.append("TickerCount")
    if state["snapshot_count"] != expected_snapshot_count:
        mismatches.append("SnapshotCount")
    if (
        state["status"] == "COMPLETED"
        and state["event_tickers"]
        and state["event_tickers"] != tuple(sorted(tickers))
    ):
        mismatches.append("TickerUniverse")
    if state["include_keys"]:
        mismatches.append("IncludeSourceKeysJson")
    if actual_excluded != expected_excluded:
        mismatches.append("ExcludeSourceKeysJson")
    if mismatches:
        raise ValueError(
            f"resume collision for evaluation run {run_id}; "
            f"mismatched={mismatches}. Use another --run-prefix."
        )


def _assert_effectiveness_compatible(
    state: dict,
    run_id: str,
    scope_type: str,
    source_key: str,
    source_family: str,
    source_role: str,
    horizon: int,
    baseline_run_id: str,
    ablation_run_id: str,
) -> None:
    expected = {
        "scope_type": scope_type,
        "source_key": source_family if scope_type == "SOURCE_FAMILY" else source_key,
        "source_family": source_family,
        "source_role": source_role,
        "horizon_bars": horizon,
        "baseline_run_id": baseline_run_id,
        "ablation_run_id": ablation_run_id,
    }
    mismatches = [key for key, value in expected.items() if state[key] != value]
    if mismatches:
        raise ValueError(
            f"resume collision for effectiveness run {run_id}; "
            f"mismatched={mismatches}. Use another --run-prefix."
        )


def _run_child(command: Sequence[str], label: str) -> None:
    print(f"\n[RS-V2.4-FULL] START {label}")
    print("[RS-V2.4-FULL] CMD   " + " ".join(command))
    subprocess.run(list(command), cwd=PROJECT_ROOT, check=True)
    print(f"[RS-V2.4-FULL] DONE  {label}")


def _evaluation_command(
    tickers: Sequence[str],
    window: EvaluationWindow,
    snapshot_step: int,
    horizon: int,
    model_version: str,
    run_id: str,
    excluded_source_keys: Sequence[str] = (),
) -> list[str]:
    command = [
        sys.executable,
        str(EVALUATION_SCRIPT),
        "--tickers",
        ",".join(tickers),
        "--start",
        window.start_date.isoformat(),
        "--end",
        window.evaluation_end.isoformat(),
        "--snapshot-step",
        str(snapshot_step),
        "--horizon-bars",
        str(horizon),
        "--model-version",
        model_version,
        "--run-id",
        run_id,
    ]
    if excluded_source_keys:
        command.extend(
            ["--exclude-source-keys", ",".join(sorted(excluded_source_keys))]
        )
    return command


def _effectiveness_command(
    baseline_run_id: str,
    ablation_run_id: str,
    spec: SourceSpec,
    scope_type: str,
    run_id: str,
    policy_json: str,
    notes: str,
) -> list[str]:
    return [
        sys.executable,
        str(EFFECTIVENESS_SCRIPT),
        "--baseline-run",
        baseline_run_id,
        "--ablation-run",
        ablation_run_id,
        "--source-key",
        spec.source_key,
        "--source-family",
        spec.source_family,
        "--source-role",
        spec.source_role,
        "--scope-type",
        scope_type,
        "--policy-json",
        policy_json,
        "--run-id",
        run_id,
        "--notes",
        notes,
    ]


def _promotion_command(
    effectiveness_run_id: str,
    policy_json: str,
    promotion_mode: str,
    decision_id: str,
    notes: str,
) -> list[str] | None:
    if promotion_mode == "skip":
        return None
    command = [
        sys.executable,
        str(PROMOTION_SCRIPT),
        "--effectiveness-run",
        effectiveness_run_id,
        "--policy-json",
        policy_json,
        "--notes",
        notes,
    ]
    if promotion_mode == "audit":
        command.extend(["--decision-id", decision_id, "--apply"])
    return command


def _maybe_run_evaluation(
    factory: DuckDBConnectionFactory,
    resume: bool,
    command: Sequence[str],
    run_id: str,
    window: EvaluationWindow,
    horizon: int,
    excluded_source_keys: Sequence[str],
    tickers: Sequence[str],
    expected_snapshot_count: int,
    label: str,
) -> None:
    with factory.reader() as connection:
        state = _evaluation_run_state(connection, run_id)
    if state is not None:
        _assert_evaluation_compatible(
            state,
            run_id,
            window,
            horizon,
            excluded_source_keys,
            tickers,
            expected_snapshot_count,
        )
        if resume and state["status"] == "COMPLETED":
            print(f"[RS-V2.4-FULL] REUSE {label} run_id={run_id}")
            return
    _run_child(command, label)


def _maybe_run_effectiveness(
    factory: DuckDBConnectionFactory,
    resume: bool,
    command: Sequence[str],
    run_id: str,
    scope_type: str,
    spec: SourceSpec,
    horizon: int,
    baseline_run_id: str,
    ablation_run_id: str,
    label: str,
) -> None:
    with factory.reader() as connection:
        state = _effectiveness_run_state(connection, run_id)
    if state is not None:
        _assert_effectiveness_compatible(
            state,
            run_id,
            scope_type,
            spec.source_key,
            spec.source_family,
            spec.source_role,
            horizon,
            baseline_run_id,
            ablation_run_id,
        )
        if resume and state["status"] == "COMPLETED":
            print(f"[RS-V2.4-FULL] REUSE {label} run_id={run_id}")
            return
    _run_child(command, label)


def main() -> None:
    args = _parse_args()
    _check_child_scripts()

    horizons = _parse_horizons(args.horizons)
    scopes = _parse_scopes(args.scopes)
    if args.snapshot_step <= 0:
        raise ValueError("--snapshot-step must be > 0")

    effectiveness_policy_json = json.dumps(
        _parse_json_object(
            args.effectiveness_policy_json,
            "--effectiveness-policy-json",
        ),
        sort_keys=True,
    )
    promotion_policy_json = json.dumps(
        _parse_json_object(
            args.promotion_policy_json,
            "--promotion-policy-json",
        ),
        sort_keys=True,
    )
    extra_specs = _parse_extra_source_specs(args.extra_source_specs_json)
    explicit_tickers = _parse_csv(args.tickers)
    only_source_keys = _parse_csv(args.only_source_keys)
    skip_source_keys = _parse_csv(args.skip_source_keys)
    overlap = set(only_source_keys) & set(skip_source_keys)
    if overlap:
        raise ValueError(
            f"source keys cannot be both selected and skipped: {sorted(overlap)}"
        )

    factory = DuckDBConnectionFactory(db_path=settings.local_db_path)
    with factory.reader() as connection:
        window = _resolve_window(
            connection,
            horizons,
            args.start,
            args.end,
            args.lookback_years,
            args.freshness_bars,
        )
        tickers = _resolve_tickers(
            connection,
            window,
            explicit_tickers,
            args.min_history_bars,
            args.max_tickers,
        )
        expected_snapshot_count = _expected_snapshot_count(
            connection,
            tickers,
            window,
            args.snapshot_step,
        )

    month_tag = _month_tag(args.run_month)
    run_prefix = _build_run_prefix(
        args.run_prefix,
        month_tag,
        window.evaluation_end,
        tickers,
        args.snapshot_step,
    )
    baseline_runs = {
        horizon: f"{run_prefix}_BASE_H{horizon}" for horizon in horizons
    }

    print(
        json.dumps(
            {
                "monthly_full_evaluation_plan": {
                    "run_prefix": run_prefix,
                    "run_month": month_tag,
                    "start": window.start_date.isoformat(),
                    "evaluation_end": window.evaluation_end.isoformat(),
                    "latest_data_date": window.latest_data_date.isoformat(),
                    "future_outcome_bars_reserved": max(horizons),
                    "ticker_count": len(tickers),
                    "tickers_preview": list(tickers[:20]),
                    "expected_snapshot_count": expected_snapshot_count,
                    "horizons": list(horizons),
                    "scopes": list(scopes),
                    "snapshot_step": args.snapshot_step,
                    "promotion_mode": args.promotion_mode,
                    "resume": args.resume,
                }
            },
            indent=2,
            sort_keys=True,
        )
    )

    if args.plan_only:
        print(
            json.dumps(
                {
                    "plan_only": True,
                    "baseline_runs": baseline_runs,
                    "source_discovery": "deferred_until_completed_baseline",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    # One baseline per horizon; every source/family ablation reuses it.
    for horizon in horizons:
        run_id = baseline_runs[horizon]
        command = _evaluation_command(
            tickers,
            window,
            args.snapshot_step,
            horizon,
            "RS_V2_4_BASELINE",
            run_id,
        )
        _maybe_run_evaluation(
            factory,
            args.resume,
            command,
            run_id,
            window,
            horizon,
            (),
            tickers,
            expected_snapshot_count,
            f"baseline H{horizon}",
        )

    catalog_baseline_run = baseline_runs[horizons[0]]
    with factory.reader() as connection:
        full_catalog, lineage = _discover_source_catalog(
            connection,
            catalog_baseline_run,
            extra_specs,
        )

    config_specs = _select_config_specs(
        full_catalog,
        lineage,
        only_source_keys,
        skip_source_keys,
    )
    family_groups = _family_groups(
        full_catalog,
        config_specs,
    )

    print(
        json.dumps(
            {
                "source_catalog": [
                    {
                        "source_key": spec.source_key,
                        "source_family": spec.source_family,
                        "source_role": spec.source_role,
                    }
                    for spec in config_specs
                ],
                "source_count": len(config_specs),
                "family_count": len(family_groups),
                "baseline_lineage_key_count": len(lineage),
            },
            indent=2,
            sort_keys=True,
        )
    )

    notes = f"Monthly R/S V2.4 full evaluation {run_prefix}"
    effectiveness_runs: list[str] = []

    for horizon in horizons:
        baseline_run_id = baseline_runs[horizon]

        if "SOURCE_CONFIG" in scopes:
            for spec in config_specs:
                excluded = (spec.source_key,)
                model_version = _ablation_model_version(
                    "SOURCE_CONFIG",
                    spec.source_key,
                    excluded,
                )
                ablation_run_id = (
                    f"{run_prefix}_ABL_SRC_{_slug(spec.source_key, 32)}_H{horizon}"
                )
                _maybe_run_evaluation(
                    factory,
                    args.resume,
                    _evaluation_command(
                        tickers,
                        window,
                        args.snapshot_step,
                        horizon,
                        model_version,
                        ablation_run_id,
                        excluded,
                    ),
                    ablation_run_id,
                    window,
                    horizon,
                    excluded,
                    tickers,
                    expected_snapshot_count,
                    f"ablation SOURCE_CONFIG {spec.source_key} H{horizon}",
                )

                effectiveness_run_id = (
                    f"{run_prefix}_EFF_SRC_{_slug(spec.source_key, 32)}_H{horizon}"
                )
                _maybe_run_effectiveness(
                    factory,
                    args.resume,
                    _effectiveness_command(
                        baseline_run_id,
                        ablation_run_id,
                        spec,
                        "SOURCE_CONFIG",
                        effectiveness_run_id,
                        effectiveness_policy_json,
                        notes,
                    ),
                    effectiveness_run_id,
                    "SOURCE_CONFIG",
                    spec,
                    horizon,
                    baseline_run_id,
                    ablation_run_id,
                    f"effectiveness SOURCE_CONFIG {spec.source_key} H{horizon}",
                )
                effectiveness_runs.append(effectiveness_run_id)

                command = _promotion_command(
                    effectiveness_run_id,
                    promotion_policy_json,
                    args.promotion_mode,
                    (
                        f"RSSRC_{run_prefix}_SRC_"
                        f"{_slug(spec.source_key, 28)}_H{horizon}"
                    ),
                    notes,
                )
                if command is not None:
                    _run_child(
                        command,
                        f"promotion SOURCE_CONFIG {spec.source_key} H{horizon}",
                    )

        if "SOURCE_FAMILY" in scopes:
            for (family, role), member_keys in family_groups.items():
                family_spec = SourceSpec(family, family, role)
                model_version = _ablation_model_version(
                    "SOURCE_FAMILY",
                    family,
                    member_keys,
                )
                ablation_run_id = (
                    f"{run_prefix}_ABL_FAM_{_slug(family, 32)}_H{horizon}"
                )
                _maybe_run_evaluation(
                    factory,
                    args.resume,
                    _evaluation_command(
                        tickers,
                        window,
                        args.snapshot_step,
                        horizon,
                        model_version,
                        ablation_run_id,
                        member_keys,
                    ),
                    ablation_run_id,
                    window,
                    horizon,
                    member_keys,
                    tickers,
                    expected_snapshot_count,
                    f"ablation SOURCE_FAMILY {family} H{horizon}",
                )

                effectiveness_run_id = (
                    f"{run_prefix}_EFF_FAM_{_slug(family, 32)}_H{horizon}"
                )
                _maybe_run_effectiveness(
                    factory,
                    args.resume,
                    _effectiveness_command(
                        baseline_run_id,
                        ablation_run_id,
                        family_spec,
                        "SOURCE_FAMILY",
                        effectiveness_run_id,
                        effectiveness_policy_json,
                        notes,
                    ),
                    effectiveness_run_id,
                    "SOURCE_FAMILY",
                    family_spec,
                    horizon,
                    baseline_run_id,
                    ablation_run_id,
                    f"effectiveness SOURCE_FAMILY {family} H{horizon}",
                )
                effectiveness_runs.append(effectiveness_run_id)

                command = _promotion_command(
                    effectiveness_run_id,
                    promotion_policy_json,
                    args.promotion_mode,
                    (
                        f"RSSRC_{run_prefix}_FAM_"
                        f"{_slug(family, 28)}_H{horizon}"
                    ),
                    notes,
                )
                if command is not None:
                    _run_child(
                        command,
                        f"promotion SOURCE_FAMILY {family} H{horizon}",
                    )

    print(
        json.dumps(
            {
                "monthly_full_evaluation_status": "COMPLETED",
                "run_prefix": run_prefix,
                "ticker_count": len(tickers),
                "source_count": len(config_specs),
                "family_count": len(family_groups),
                "horizons": list(horizons),
                "effectiveness_run_count": len(effectiveness_runs),
                "promotion_mode": args.promotion_mode,
                "public_view": '"CherryMon"."main"."vw_RS_Source_Effectiveness"',
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
