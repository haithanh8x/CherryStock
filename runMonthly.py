"""CherryStock monthly runner.

`run.py` is the daily operational pipeline.
`runMonthly.py` is the entry point for heavier jobs that should run monthly.

Phase 1 monthly job:
    scripts/run_rs_v2_4_full_evaluation.py

Usage:
    python runMonthly.py

All CLI arguments are forwarded to the current monthly job, for example:
    python runMonthly.py --plan-only
    python runMonthly.py --tickers MWG,FPT,HPG --horizons 20 --plan-only
    python runMonthly.py --run-month 2026-09
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parent

MONTHLY_JOBS: tuple[dict[str, object], ...] = (
    {
        "key": "rs_v2_4_full_evaluation",
        "title": "R/S V2.4 Full Source Effectiveness Evaluation",
        "script": PROJECT_ROOT / "scripts" / "run_rs_v2_4_full_evaluation.py",
        "forward_cli_args": True,
    },
)


def _run_job(job: dict[str, object], cli_args: list[str]) -> None:
    """Run one monthly job as a child process and fail fast on errors."""
    script = Path(job["script"])
    if not script.exists():
        raise FileNotFoundError(f"Monthly job script not found: {script}")

    command = [sys.executable, str(script)]
    if bool(job.get("forward_cli_args", False)):
        command.extend(cli_args)

    print(f"▶ {job['title']}")
    print(f"  Script: {script.relative_to(PROJECT_ROOT)}")

    started = perf_counter()
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )
    elapsed = perf_counter() - started

    print(f"✓ {job['title']} completed in {elapsed:.1f}s")


def main() -> None:
    """Run all configured monthly jobs sequentially."""
    cli_args = sys.argv[1:]

    print("CherryStock Monthly Run")
    print(f"Jobs: {len(MONTHLY_JOBS)}")

    total_started = perf_counter()
    for index, job in enumerate(MONTHLY_JOBS, start=1):
        print(f"\n[{index}/{len(MONTHLY_JOBS)}]")
        _run_job(job, cli_args)

    elapsed = perf_counter() - total_started
    print(f"\n✓ Monthly Run completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
