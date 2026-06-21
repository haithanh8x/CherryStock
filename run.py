import duckdb
import pandas as pd
import sys
import io

from CrawlStock.readAmi import syncAmibroker_EOD, syncAmibroker_Intraday
from lstPara import getCherryMon_local, getCherryMon_motherDuck

# --- HÀM MAIN ---
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

    syncAmibroker_EOD(getCherryMon_local())
    syncAmibroker_Intraday(getCherryMon_local())