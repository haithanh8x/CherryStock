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
