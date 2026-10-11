"""Read-only, point-in-time R/S Volume Profile ablation and score diagnostics.

Compare baseline/challenger events on identical ticker/date/rank/type and
price-compatible levels; report changed geometry and unmatched rows separately.
Strength-only changes cannot change price-based outcome labels on the same level.
Research evidence only; no model promotion or database writes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.Ults.DuckLib import DuckDBManager  # noqa: E402

SPLITS = ("VALIDATION", "TEST")
KEYS = ("Ticker", "AsOfDate", "Split", "LevelRank", "LevelType")
OUTCOMES = ("Touched", "Held", "Broken", "Retested")
METRICS = ("hold_after_touch", "break_after_touch", "retest_after_break")
REQUIRED = set(KEYS) | {"EvaluationRunId", "LevelPrice", "StrengthScore", "Regime"} | set(OUTCOMES)


def _rates(rows: pd.DataFrame) -> dict:
    """Conditional outcome rates: missing denominator means NaN, never zero."""
    touched = rows.loc[rows["Touched"].eq(True)]  # noqa: E712
    broken = touched.loc[touched["Broken"].eq(True)]  # noqa: E712
    return {
        "events": int(len(rows)),
        "touches": int(len(touched)),
        "hold_after_touch": float(touched["Held"].eq(True).mean()) if len(touched) else float("nan"),
        "break_after_touch": float(touched["Broken"].eq(True).mean()) if len(touched) else float("nan"),
        "retest_after_break": float(broken["Retested"].eq(True).mean()) if len(broken) else float("nan"),
    }


def summarize_event_runs(events: pd.DataFrame) -> pd.DataFrame:
    """Unpaired, descriptive metrics only; NOT promotion-quality causal evidence."""
    expected = {"EvaluationRunId", "Ticker", "AsOfDate", "Split", *OUTCOMES}
    missing = expected - set(events)
    if missing:
        raise ValueError(f"missing event columns: {sorted(missing)}")
    if events.empty:
        raise ValueError("no evaluation events for requested run IDs")
    relevant = events.loc[events["Split"].isin(SPLITS)]
    if relevant.empty:
        raise ValueError("no VALIDATION/TEST events")
    rows = []
    for (run_id, split), group in relevant.groupby(["EvaluationRunId", "Split"], sort=True):
        row = {"run_id": str(run_id), "split": str(split),
               "unique_ticker_dates": int(group[["Ticker", "AsOfDate"]].drop_duplicates().shape[0])}
        row.update(_rates(group))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["split", "run_id"]).reset_index(drop=True)


def compare_baseline(summary: pd.DataFrame, baseline_id: str) -> pd.DataFrame:
    """Backward-compatible UNPAIRED view; prefer compare_matched_runs()."""
    base = summary.loc[summary["run_id"] == baseline_id].set_index("split")
    if base.empty:
        raise ValueError("baseline ID not found in VALIDATION/TEST metrics")
    output = summary.copy()
    for metric in METRICS:
        output[f"delta_{metric}"] = output.apply(
            lambda row: (row[metric] - base.loc[row["split"], metric]
                         if row["split"] in base.index else float("nan")), axis=1,
        )
    output["coverage_matches_baseline"] = output.apply(
        lambda row: (int(row["unique_ticker_dates"])
                     == int(base.loc[row["split"], "unique_ticker_dates"])
                     if row["split"] in base.index else False), axis=1,
    )
    return output


def _validated_events(events: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    missing = REQUIRED - set(events)
    if missing:
        raise ValueError(f"missing event columns: {sorted(missing)}")
    if not ids or len(set(ids)) != len(ids) or len(ids) < 2:
        raise ValueError("provide distinct baseline and challenger IDs")
    frame = events.loc[events["Split"].isin(SPLITS) & events["EvaluationRunId"].isin(ids)].copy()
    for run in ids:
        run_frame = frame.loc[frame["EvaluationRunId"] == run]
        if set(run_frame["Split"].unique()) != set(SPLITS):
            raise ValueError(f"run {run!r} must have VALIDATION and TEST events")
        if run_frame.duplicated(list(KEYS)).any():
            raise ValueError(f"duplicate evaluation identity in run {run!r}")
        if run_frame[list(KEYS)].isna().any().any():
            raise ValueError(f"null evaluation identity in run {run!r}")
        price = pd.to_numeric(run_frame["LevelPrice"], errors="coerce")
        if price.isna().any() or (price <= 0).any():
            raise ValueError(f"nonpositive/invalid LevelPrice in run {run!r}")
        score = pd.to_numeric(run_frame["StrengthScore"], errors="coerce")
        if score.isna().any():
            raise ValueError(f"invalid StrengthScore in run {run!r}")
    return frame


def align_level_events(
    events: pd.DataFrame,
    baseline_id: str,
    challenger_id: str,
    *,
    price_tolerance_pct: float = 0.005,
    strong_threshold: float = 80.0,
) -> pd.DataFrame:
    """Full outer join; unmatched/shifted price levels never masquerade as matched."""
    if not 0 <= price_tolerance_pct <= 0.05:
        raise ValueError("price_tolerance_pct must be within [0, 0.05]")
    if not 0 <= strong_threshold <= 100:
        raise ValueError("strong_threshold must be between 0 and 100")
    frame = _validated_events(events, [baseline_id, challenger_id])
    columns = [*KEYS, "LevelPrice", "StrengthScore", "Regime", *OUTCOMES]
    baseline = frame.loc[frame["EvaluationRunId"] == baseline_id, columns]
    challenger = frame.loc[frame["EvaluationRunId"] == challenger_id, columns]
    joined = baseline.merge(
        challenger, on=list(KEYS), how="outer", validate="one_to_one",
        suffixes=("_baseline", "_candidate"), indicator=True,
    )
    both = joined["_merge"].eq("both")
    prices_b = pd.to_numeric(joined["LevelPrice_baseline"], errors="coerce")
    prices_c = pd.to_numeric(joined["LevelPrice_candidate"], errors="coerce")
    joined["price_delta_pct"] = (prices_c / prices_b - 1.0) * 100.0
    joined["score_delta"] = (
        pd.to_numeric(joined["StrengthScore_candidate"], errors="coerce")
        - pd.to_numeric(joined["StrengthScore_baseline"], errors="coerce")
    )
    joined["score_changed"] = both & joined["score_delta"].abs().gt(0.005)
    joined["strong_baseline"] = joined["StrengthScore_baseline"].ge(strong_threshold)
    joined["strong_candidate"] = joined["StrengthScore_candidate"].ge(strong_threshold)
    joined["strong_cross_up"] = both & ~joined["strong_baseline"] & joined["strong_candidate"]
    joined["strong_cross_down"] = both & joined["strong_baseline"] & ~joined["strong_candidate"]
    geometry_match = both & joined["price_delta_pct"].abs().le(price_tolerance_pct * 100)
    regime_match = (joined["Regime_baseline"].fillna("UNKNOWN")
                    == joined["Regime_candidate"].fillna("UNKNOWN"))
    joined["matched_level"] = geometry_match & regime_match
    joined["event_status"] = "MATCHED"
    joined.loc[joined["_merge"].eq("left_only"), "event_status"] = "BASELINE_ONLY"
    joined.loc[joined["_merge"].eq("right_only"), "event_status"] = "CHALLENGER_ONLY"
    joined.loc[both & ~geometry_match, "event_status"] = "PRICE_CHANGED"
    joined.loc[both & geometry_match & ~regime_match, "event_status"] = "REGIME_MISMATCH"
    identical = both.copy()
    for name in OUTCOMES:
        identical &= (
            joined[f"{name}_baseline"].fillna("MISSING")
            == joined[f"{name}_candidate"].fillna("MISSING")
        )
    joined["identical_outcomes"] = identical
    joined["diagnosis"] = "UNMATCHED_OR_CHANGED_LEVEL"
    joined.loc[joined["matched_level"], "diagnosis"] = "NO_SCORE_OR_OUTCOME_CHANGE"
    joined.loc[joined["matched_level"] & joined["score_changed"] & joined["identical_outcomes"],
               "diagnosis"] = "SCORE_ONLY_NO_OUTCOME_CHANGE"
    joined.loc[joined["matched_level"] & ~joined["identical_outcomes"],
               "diagnosis"] = "OUTCOME_CHANGED"
    joined.insert(0, "baseline_run_id", baseline_id)
    joined.insert(1, "run_id", challenger_id)
    return joined.drop(columns=["_merge"]).sort_values(
        ["Split", "Ticker", "AsOfDate", "LevelType", "LevelRank"]
    ).reset_index(drop=True)


def _comparable_rates(rows: pd.DataFrame, suffix: str, strong_only: bool = False) -> dict:
    part = rows
    if strong_only:
        part = rows.loc[rows[f"strong_{suffix}"]]
    return _rates(part.rename(columns={f"{outcome}_{suffix}": outcome for outcome in OUTCOMES}))


def _hold_score_auc(rows: pd.DataFrame, suffix: str) -> float:
    """AUC: can higher Strength discriminate future holds among touched levels?

    AUC uses only point-in-time Strength scores and observed future labels.
    Return NaN unless both held and failed outcomes exist. It is NOT a
    calibrated probability and should be reviewed with the touched sample size.
    """
    touched = rows.loc[
        rows[f"Touched_{suffix}"].eq(True)
        & rows[f"Held_{suffix}"].isin([True, False])
    ].copy()
    if touched.empty:
        return float("nan")
    values = pd.to_numeric(touched[f"StrengthScore_{suffix}"], errors="coerce")
    touched = touched.loc[values.notna()]
    if touched.empty:
        return float("nan")
    held = touched[f"Held_{suffix}"].eq(True)
    n_pos = int(held.sum())
    n_neg = int((~held).sum())
    if not n_pos or not n_neg:
        return float("nan")
    ranks = pd.to_numeric(touched[f"StrengthScore_{suffix}"]).rank(method="average")
    return float((ranks.loc[held].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _scope_report(
    joined: pd.DataFrame, scope: str, scope_key: str, split: str,
    baseline: pd.DataFrame, challenger: pd.DataFrame,
    *,
    strong_threshold: float,
) -> dict:
    pair = joined.loc[joined["matched_level"]]
    b = _comparable_rates(pair, "baseline")
    c = _comparable_rates(pair, "candidate")
    strong_b = _comparable_rates(pair, "baseline", strong_only=True)
    strong_c = _comparable_rates(pair, "candidate", strong_only=True)
    baseline_auc = _hold_score_auc(pair, "baseline")
    challenger_auc = _hold_score_auc(pair, "candidate")
    all_baseline = baseline[["Ticker", "AsOfDate"]].drop_duplicates()
    all_candidate = challenger[["Ticker", "AsOfDate"]].drop_duplicates()
    snapshot_overlap = all_baseline.merge(all_candidate, on=["Ticker", "AsOfDate"], how="inner")
    statuses = joined["event_status"].value_counts()
    row = {
        "run_id": joined["run_id"].iloc[0],
        "baseline_run_id": joined["baseline_run_id"].iloc[0],
        "split": split, "scope": scope, "scope_key": scope_key,
        "baseline_total_events": len(baseline),
        "candidate_total_events": len(challenger),
        "baseline_snapshots": len(all_baseline),
        "candidate_snapshots": len(all_candidate),
        "matched_snapshots": len(snapshot_overlap),
        "coverage_matches_baseline": (
            len(snapshot_overlap) == len(all_baseline) == len(all_candidate)
        ),
        "matched_levels": int(len(pair)),
        "baseline_only_levels": int(statuses.get("BASELINE_ONLY", 0)),
        "candidate_only_levels": int(statuses.get("CHALLENGER_ONLY", 0)),
        "price_changed_levels": int(statuses.get("PRICE_CHANGED", 0)),
        "regime_mismatch_levels": int(statuses.get("REGIME_MISMATCH", 0)),
        "score_changed_levels": int(pair["score_changed"].sum()),
        "identical_outcome_levels": int(pair["identical_outcomes"].sum()),
        "strong_cross_up": int(pair["strong_cross_up"].sum()),
        "strong_cross_down": int(pair["strong_cross_down"].sum()),
        "strong_threshold": strong_threshold,
        "baseline_hold_strength_auc": baseline_auc,
        "hold_strength_auc": challenger_auc,
        "delta_hold_strength_auc": challenger_auc - baseline_auc,
        "baseline_strong_events": strong_b["events"],
        "candidate_strong_events": strong_c["events"],
        "baseline_strong_touches": strong_b["touches"],
        "candidate_strong_touches": strong_c["touches"],
        "baseline_strong_hold_after_touch": strong_b["hold_after_touch"],
        "candidate_strong_hold_after_touch": strong_c["hold_after_touch"],
        "delta_strong_hold_after_touch": (
            strong_c["hold_after_touch"] - strong_b["hold_after_touch"]
        ),
        "baseline_touches": b["touches"],
        "touches": c["touches"],
        "events": c["events"],
        "fully_matched_levels": (
            len(pair) == len(baseline) == len(challenger)
            and int(statuses.get("REGIME_MISMATCH", 0)) == 0
        ),
    }
    for metric in METRICS:
        row[f"baseline_{metric}"] = b[metric]
        row[metric] = c[metric]
        row[f"delta_{metric}"] = c[metric] - b[metric]
    row["paired_evidence_eligible"] = (
        row["coverage_matches_baseline"] and row["fully_matched_levels"]
        and row["baseline_touches"] > 0 and row["touches"] > 0
    )
    # Repository PromotionPolicy: at least 200 VALIDATION / 100 TEST events.
    # This is a *sample gate only*: positive OOS lift, regime stability,
    # complexity, and independent reviewer approval must still be verified.
    min_events = 200 if split == "VALIDATION" else 100
    row["min_events_required"] = min_events
    row["adequate_sample_size"] = min(row["baseline_total_events"],
                                      row["candidate_total_events"],
                                      row["matched_levels"]) >= min_events
    row["promotion_evidence_eligible"] = (
        row["paired_evidence_eligible"] and row["adequate_sample_size"]
    )
    return row


def compare_matched_runs(
    events: pd.DataFrame,
    baseline_id: str,
    challenger_ids: list[str],
    *,
    price_tolerance_pct: float = 0.005,
    strong_threshold: float = 80.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return paired evidence by split/ticker/regime and full event-level audit.

    Outcomes are paired only for same rank/type with price- and regime-compatible
    levels. Unmatched levels stay visible and block matched-evidence eligibility.
    For model changes that alter levels, evaluate changed selections separately.
    """
    ids = [baseline_id, *challenger_ids]
    frame = _validated_events(events, ids)
    aligned = [
        align_level_events(
            frame, baseline_id, run_id,
            price_tolerance_pct=price_tolerance_pct, strong_threshold=strong_threshold,
        )
        for run_id in challenger_ids
    ]
    audit = pd.concat(aligned, ignore_index=True)
    rows: list[dict] = []
    for run_id in challenger_ids:
        subset = audit.loc[audit["run_id"] == run_id]
        for split in SPLITS:
            b_all = frame.loc[(frame["EvaluationRunId"] == baseline_id) & (frame["Split"] == split)]
            c_all = frame.loc[(frame["EvaluationRunId"] == run_id) & (frame["Split"] == split)]
            selected = subset.loc[subset["Split"] == split]
            rows.append(_scope_report(selected, "ALL", "ALL", split, b_all, c_all,
                                      strong_threshold=strong_threshold))
            for ticker in sorted(set(b_all["Ticker"]) | set(c_all["Ticker"])):
                b = b_all.loc[b_all["Ticker"] == ticker]
                c = c_all.loc[c_all["Ticker"] == ticker]
                sub = selected.loc[selected["Ticker"] == ticker]
                if not sub.empty:
                    rows.append(_scope_report(sub, "TICKER", str(ticker), split, b, c,
                                              strong_threshold=strong_threshold))
            regimes = sorted(
                set(b_all["Regime"].dropna()) | set(c_all["Regime"].dropna())
            )
            for regime in regimes:
                b = b_all.loc[b_all["Regime"] == regime]
                c = c_all.loc[c_all["Regime"] == regime]
                sub = selected.loc[
                    selected["Regime_baseline"].eq(regime)
                    | selected["Regime_candidate"].eq(regime)
                ]
                if not sub.empty:
                    rows.append(_scope_report(sub, "REGIME", str(regime), split, b, c,
                                              strong_threshold=strong_threshold))
    return pd.DataFrame(rows), audit


def _evidence_path(path: str) -> Path:
    out = (PROJECT_ROOT / path).resolve()
    root = (PROJECT_ROOT / "docs/reference/data").resolve()
    if root not in out.parents:
        raise ValueError("output must be inside docs/reference/data/")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Paired R/S Volume Profile ablation and DISTANCE_AWARE score diagnostics"
    )
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--challenger-run-ids", required=True)
    parser.add_argument("--price-tolerance-pct", type=float, default=0.005,
                        help="Maximum price deviation for a matched level (fraction, default 0.005)")
    parser.add_argument("--strong-threshold", type=float, default=80.0)
    parser.add_argument("--output", default="docs/reference/data/rs/volume_profile_ablation_matched.csv")
    parser.add_argument("--details-output", default="docs/reference/data/rs/volume_profile_level_diagnostics.csv")
    args = parser.parse_args()
    ids = [args.baseline_run_id] + [
        token.strip() for token in args.challenger_run_ids.split(",") if token.strip()
    ]
    if len(ids) != len(set(ids)) or len(ids) < 2:
        raise ValueError("provide distinct baseline and challenger IDs")
    placeholders = ", ".join("?" for _ in ids)
    with DuckDBManager(read_only=True) as connection:
        frame = connection.execute(
            'SELECT "EvaluationRunId", "Ticker", "AsOfDate", "Split", "Regime", '
            '"LevelRank", "LevelType", "LevelPrice", "StrengthScore", '
            '"Touched", "Held", "Broken", "Retested" '
            'FROM "CherryMon"."main"."cal_rs_evaluation_event" '
            f'WHERE "EvaluationRunId" IN ({placeholders}) '
            'ORDER BY "EvaluationRunId", "Ticker", "AsOfDate", "LevelRank"',
            ids,
        ).df()
    summary, details = compare_matched_runs(
        frame, ids[0], ids[1:],
        price_tolerance_pct=args.price_tolerance_pct, strong_threshold=args.strong_threshold,
    )
    summary_path = _evidence_path(args.output)
    details_path = _evidence_path(args.details_output)
    if summary_path == details_path:
        raise ValueError("--output and --details-output must differ")
    summary.to_csv(summary_path, index=False)
    details.to_csv(details_path, index=False)
    print(summary.loc[summary["scope"] == "ALL"].to_string(index=False))
    print(f"Paired comparison: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Event-level score/price diagnostics: {details_path.relative_to(PROJECT_ROOT)}")
    for row in summary.loc[summary["scope"] == "ALL"].to_dict("records"):
        if not row["promotion_evidence_eligible"]:
            print(f"WARNING: {row['run_id']} {row['split']} has unmatched evidence; do NOT promote.")
        if row["score_changed_levels"] and not row["strong_cross_up"] and not row["strong_cross_down"]:
            print(f"INFO: {row['run_id']} {row['split']}: Strength changed but no "
                  "threshold-80 crossing; identical price-level outcome metrics are expected.")
    print("Research-only: raw hold delta is price-level outcome; conditional AUC tests score discrimination. "
          "A positive threshold-conditioned result also needs independent OOS validation.")


if __name__ == "__main__":
    main()
