from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readAmi import syncAmibroker_EOD  # noqa: E402


def main() -> None:
    """
    Full reload all configured AmiBroker EOD sources.

    syncAmibroker_EOD(from_last_day=None) follows the existing EOD contract:
    each configured target is rebuilt from the complete source folder.
    """
    syncAmibroker_EOD(from_last_day=None)


if __name__ == "__main__":
    main()
