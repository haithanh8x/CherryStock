"""CLI entry point for monthly R/S V2.4 full Source Effectiveness evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from Orchestrator.rs_v2_4_full_evaluation import main  # noqa: E402


if __name__ == "__main__":
    main()
