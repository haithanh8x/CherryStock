"""Statistical definition checks for R/S Volume Profile read-only comparison."""
from datetime import date
import pandas as pd
import pytest

from scripts.compare_rs_volume_profile import summarize_event_runs, compare_baseline


def _events():
    rows = []
    for run, hold, broken in (
        ("BASE", [True, False], [False, True]),
        ("NEW", [True, True], [False, False]),
    ):
        for day, held, broke in zip(
            [date(2026, 1, 5), date(2026, 1, 6)], hold, broken,
        ):
            rows.append({
                "EvaluationRunId": run,
                "Ticker": "MWG",
                "AsOfDate": day,
                "Split": "TEST",
                "Touched": True,
                "Held": held,
                "Broken": broke,
                "Retested": broke,
            })
    return pd.DataFrame(rows)


def test_ablation_compare_reports_sample_size_and_delta():
    summary = summarize_event_runs(_events())
    report = compare_baseline(summary, "BASE")
    challenger = report[report["run_id"] == "NEW"].iloc[0]
    assert challenger["coverage_matches_baseline"]
    assert challenger["hold_after_touch"] == pytest.approx(1.0)
    assert challenger["delta_hold_after_touch"] == pytest.approx(0.5)
    assert challenger["delta_break_after_touch"] == pytest.approx(-0.5)
    assert challenger["touches"] == 2


def test_comparison_fails_closed_on_missing_splits_or_baseline():
    with pytest.raises(ValueError, match="baseline ID"):
        compare_baseline(summarize_event_runs(_events()), "NOT_FOUND")
    invalid = _events().assign(Split="TRAIN")
    with pytest.raises(ValueError, match="no VALIDATION/TEST"):
        summarize_event_runs(invalid)


def _paired_events():
    """One ticker, two dates in each split, stable price and identical outcomes."""
    rows = []
    for split in ("VALIDATION", "TEST"):
        for run in ("BASE", "DISTANCE"):
            for day, held, score in (
                (date(2026, 1, 5), True, 84.0 if run == "DISTANCE" else 79.0),
                (date(2026, 1, 6), False, 75.0 if run == "DISTANCE" else 85.0),
            ):
                rows.append({
                    "EvaluationRunId": run, "Ticker": "MWG", "AsOfDate": day,
                    "Split": split, "Regime": "RANGE_LOW_VOL",
                    "LevelRank": "S1", "LevelType": "SUPPORT", "LevelPrice": 95.0,
                    "StrengthScore": score, "Touched": True, "Held": held,
                    "Broken": not held, "Retested": not held,
                })
    return pd.DataFrame(rows)


def test_matched_distance_aware_detects_score_only_not_price_outcome_lift():
    from scripts.compare_rs_volume_profile import compare_matched_runs

    summary, details = compare_matched_runs(_paired_events(), "BASE", ["DISTANCE"])
    overall = summary.loc[(summary["scope"] == "ALL") & (summary["split"] == "TEST")].iloc[0]
    assert overall["promotion_evidence_eligible"]
    assert overall["matched_levels"] == 2
    assert overall["score_changed_levels"] == 2
    assert overall["identical_outcome_levels"] == 2
    assert overall["delta_hold_after_touch"] == pytest.approx(0.0)
    assert overall["strong_cross_up"] == 1
    assert overall["strong_cross_down"] == 1
    assert overall["baseline_strong_hold_after_touch"] == pytest.approx(0)
    assert overall["candidate_strong_hold_after_touch"] == pytest.approx(1)
    assert overall["delta_strong_hold_after_touch"] == pytest.approx(1)
    assert overall["baseline_hold_strength_auc"] == pytest.approx(0.0)
    assert overall["hold_strength_auc"] == pytest.approx(1.0)
    assert overall["delta_hold_strength_auc"] == pytest.approx(1.0)
    assert set(details["diagnosis"]) == {"SCORE_ONLY_NO_OUTCOME_CHANGE"}
    assert set(summary["scope"]) == {"ALL", "TICKER", "REGIME"}


def test_matched_ablation_fails_gate_on_changed_price_or_unmatched_levels():
    from scripts.compare_rs_volume_profile import compare_matched_runs

    events = _paired_events()
    changed = events.copy()
    changed.loc[(changed["EvaluationRunId"] == "DISTANCE") &
                (changed["AsOfDate"] == date(2026, 1, 6)), "LevelPrice"] = 98.0
    report, diagnostics = compare_matched_runs(changed, "BASE", ["DISTANCE"])
    overall = report.loc[(report["scope"] == "ALL") & (report["split"] == "TEST")].iloc[0]
    assert overall["matched_levels"] == 1
    assert overall["price_changed_levels"] == 1
    assert not overall["promotion_evidence_eligible"]
    assert "PRICE_CHANGED" in set(diagnostics["event_status"])

    removed = events.loc[~((events["EvaluationRunId"] == "DISTANCE") &
                           (events["AsOfDate"] == date(2026, 1, 6)))].copy()
    report, diagnostics = compare_matched_runs(removed, "BASE", ["DISTANCE"])
    overall = report.loc[(report["scope"] == "ALL") & (report["split"] == "TEST")].iloc[0]
    assert overall["baseline_only_levels"] == 1
    assert not overall["fully_matched_levels"]
    # Same ticker/date COUNT is an insufficient test; compare the event identities.
    assert set(diagnostics["event_status"]) == {"MATCHED", "BASELINE_ONLY"}


def test_matched_ablation_rejects_missing_split_and_duplicate_event_identity():
    from scripts.compare_rs_volume_profile import compare_matched_runs

    frame = _paired_events()
    truncated = frame.loc[~((frame["EvaluationRunId"] == "DISTANCE") &
                            (frame["Split"] == "VALIDATION"))]
    with pytest.raises(ValueError, match="must have VALIDATION and TEST"):
        compare_matched_runs(truncated, "BASE", ["DISTANCE"])
    duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate evaluation identity"):
        compare_matched_runs(duplicated, "BASE", ["DISTANCE"])


def test_threshold_diagnostics_require_touched_levels_for_hold_rate():
    from scripts.compare_rs_volume_profile import compare_matched_runs

    frame = _paired_events()
    frame.loc[frame["EvaluationRunId"] == "DISTANCE", "StrengthScore"] = 10.0
    summary, _ = compare_matched_runs(frame, "BASE", ["DISTANCE"])
    overall = summary.loc[(summary["scope"] == "ALL") & (summary["split"] == "TEST")].iloc[0]
    assert pd.isna(overall["candidate_strong_hold_after_touch"])
    assert pd.isna(overall["delta_strong_hold_after_touch"])
    assert overall["candidate_strong_touches"] == 0


def test_hold_auc_is_undefined_for_one_class_or_no_touch():
    from scripts.compare_rs_volume_profile import compare_matched_runs

    frame = _paired_events()
    frame["Held"] = True  # cannot discriminate with no negative label
    summary, _ = compare_matched_runs(frame, "BASE", ["DISTANCE"])
    row = summary.loc[(summary["scope"] == "ALL") & (summary["split"] == "TEST")].iloc[0]
    assert pd.isna(row["hold_strength_auc"])
    assert pd.isna(row["delta_hold_strength_auc"])
