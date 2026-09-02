"""One-off: run archived V2.3 golden regression with correct sys.path.

The golden script was moved to scripts/Archive/ on this branch, which broke its
PROJECT_ROOT resolution (parents[1] now points at scripts/). This wrapper keeps
the archived script untouched and runs it as-is.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

# Patch PROJECT_ROOT before exec: the archived script computes it from
# parents[1], which is scripts/ after the move, so we exec its source with a
# corrected assignment.
source = (ROOT / "scripts" / "Archive" / "run_rs_v2_3_golden.py").read_text(
    encoding="utf-8"
)
source = source.replace(
    "PROJECT_ROOT = Path(__file__).resolve().parents[1]",
    "PROJECT_ROOT = Path(r'C:/Github/CherryStock')",
)

module_namespace: dict = {"__name__": "rs_v2_3_golden_wrapper"}
exec(compile(source, str(ROOT / "scripts" / "Archive" / "run_rs_v2_3_golden.py"), "exec"), module_namespace)
module_namespace["main"]()
