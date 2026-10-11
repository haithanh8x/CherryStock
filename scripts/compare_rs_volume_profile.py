"""Read-only R/S Volume Profile ablation comparison for existing V2.3 runs.

Prerequisite: run scripts/run_rs_v2_3_evaluation.py for the candidate variants.
All output is reference evidence, NOT approval to promote or deploy a model.
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


def summarize_event_runs(events: pd.DataFrame) -> pd.DataFrame:
    """Metrics are calculated on observed touch/break outcomes, per temporal split."""
    expected = {
        "EvaluationRunId", "Ticker", "AsOfDate", "Split", "Touched",
        "Held", "Broken", "Retested",
    }
    if expected - set(events):
        raise ValueError(f"missing event columns: {sorted(expected - set(events))}")
    if events.empty:
        raise ValueError("no evaluation events for requested run IDs")
    relevant = events[events["Split"].isin(["VALIDATION", "TEST"])].copy()
    if relevant.empty:
        raise ValueError("no VALIDATION/TEST events")
    rows = []
    for (run_id, split), group in relevant.groupby(["EvaluationRunId", "Split"], sort=True):
        touched = group.loc[group["Touched"] == True]  # noqa: E712
        broken = touched.loc[touched["Broken"] == True]  # noqa: E712
        rows.append({
            "run_id": str(run_id),
            "split": str(split),
            "events": int(len(group)),
            "unique_ticker_dates": int(group[["Ticker", "AsOfDate"]].drop_duplicates().shape[0]),
            "touches": int(len(touched)),
            "hold_after_touch": (float((touched["Held"] == True).mean())  # noqa: E712
                                 if len(touched) else float("nan")),
            "break_after_touch": (float((touched["Broken"] == True).mean())  # noqa: E712
                                  if len(touched) else float("nan")),
            "retest_after_break": (float((broken["Retested"] == True).mean())  # noqa: E712
                                   if len(broken) else float("nan")),
            # Break+retest is an *imperfect proxy*, not a verified false breakout.
        })
    return pd.DataFrame(rows).sort_values(["split", "run_id"]).reset_index(drop=True)


def compare_baseline(summary: pd.DataFrame, baseline_id: str) -> pd.DataFrame:
    base = summary.loc[summary["run_id"] == baseline_id].set_index("split")
    if base.empty:
        raise ValueError("baseline ID not found in VALIDATION/TEST metrics")
    output = summary.copy()
    for metric in ("hold_after_touch", "break_after_touch", "retest_after_break"):
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare R/S Volume Profile historical validation/test events"
    )
    parser.add_argument("--baseline-run-id", required=True)
    parser.add_argument("--challenger-run-ids", required=True,
                        help="Comma-separated ablation/challenger evaluation run IDs")
    parser.add_argument("--output", default=(
        "docs/reference/data/rs/volume_profile_ablation_comparison.csv"
    ))
    args = parser.parse_args()
    ids = [args.baseline_run_id] + [
        token.strip() for token in args.challenger_run_ids.split(",") if token.strip()
    ]
    if len(ids) != len(set(ids)) or len(ids) < 2:
        raise ValueError("provide distinct baseline and challenger IDs")
    placeholders = ", ".join("?" for _ in ids)
    with DuckDBManager(read_only=True) as connection:
        frame = connection.execute(
            'SELECT "EvaluationRunId", "Ticker", "AsOfDate", "Split", '
            '"Touched", "Held", "Broken", "Retested" '
            'FROM "CherryMon"."main"."cal_rs_evaluation_event" '
            f'WHERE "EvaluationRunId" IN ({placeholders}) '
            'ORDER BY "EvaluationRunId", "Ticker", "AsOfDate", "LevelRank"',
            ids,
        ).df()
    observed = set(frame["EvaluationRunId"].unique())
    missing = set(ids) - observed
    if missing:
        raise ValueError(f"missing R/S evaluation run IDs: {sorted(missing)}")
    summary = compare_baseline(summarize_event_runs(frame), args.baseline_run_id)
    out = (PROJECT_ROOT / args.output).resolve()
    evidence_root = (PROJECT_ROOT / "docs/reference/data").resolve()
    if evidence_root not in out.parents:
        raise ValueError("output must be inside docs/reference/data/")
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out, index=False)
    print(summary.to_string(index=False))
    print(f"Research evidence written: {out.relative_to(PROJECT_ROOT)}")
    if not bool(summary["coverage_matches_baseline"].all()):
        print("WARNING: snapshot coverage differs; comparisons are not matched-sample evidence.")
    print("Research-only: do NOT promote without V2.4 source/model gates.")


if __name__ == "__main__":
    main()
