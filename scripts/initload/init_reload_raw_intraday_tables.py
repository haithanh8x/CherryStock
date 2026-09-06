from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readAmi import syncAmibroker_Intraday  # noqa: E402


def main() -> None:
    """
    Reset and fully reload all configured AmiBroker Intraday targets.

    Sources:
    - Intraday/futures
    - Intraday/index
    - Intraday/stock
    - Intraday/warrant
    """
    syncAmibroker_Intraday(from_last_day=None, reset=True)


if __name__ == "__main__":
    main()
