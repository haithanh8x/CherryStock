from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from CrawlStock.readAmi import syncAmibroker_EOD, syncAmibroker_Intraday  # noqa: E402


def main() -> None:
    """
    Full reload all AmiBroker market data managed by CherryStock.

    Order:
    1. Full EOD reload for every configured EOD source.
    2. Reset and full reload all configured Intraday sources.

    This script is destructive for the managed raw EOD/Intraday targets because
    full-load mode rebuilds those datasets from their AmiBroker source folders.
    """
    print("=" * 72)
    print("CherryStock - FULL AMIBROKER MARKET DATA RELOAD")
    print("=" * 72)

    print("[1/2] Full reload AmiBroker EOD...")
    syncAmibroker_EOD(from_last_day=None)

    print("[2/2] Full reload AmiBroker Intraday...")
    syncAmibroker_Intraday(from_last_day=None, reset=True)

    print("=" * 72)
    print("Full AmiBroker market data reload completed.")
    print("=" * 72)


if __name__ == "__main__":
    main()
