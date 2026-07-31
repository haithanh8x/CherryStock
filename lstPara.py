"""Global Configuration and Constants Module.

This module centralizes all global variables, environment paths, system configurations,
and stock ticker lists used across the project. It provides hints and descriptions
visible within VS Code for better maintainability.

Attributes:
    lstTicker (list[list[str]]): List containing stock tickers for processing.
    VAR_USER_AGENT (str): Standard HTTP User-Agent string for request headers.
    VAR_DATAFILE_FOLDER (str): Resolved path to the local OneDrive Datafile directory,
        defaulting to 'C:\\Datafile\\' if OneDrive is not found.
    DB_PATH_CHERRYMON (str): Absolute file path to the 'CherryMon.duckdb' database.
    DATAFILE_PATH (Path): Path object pointing to the global project data directory.
"""

from datetime import date
import os
from pathlib import Path

from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta

load_dotenv(Path(__file__).resolve().parent / ".env")

# --- TICKER CONFIGURATION ---
# Full ticker list preserved for future reference
# fmt: off
# lstTicker = [
#     ["AAH"],["AAS"],["ABB"],["AAA"],["ACV"],["ACB"],["AFX"],["AGG"],["ANT"],["AGR"],["APH"],["ANV"],["BAF"],["APS"],["BCM"],["BFC"],["BIC"],["BID"],["BMI"],["BMP"],["BSI"],["BSR"],["BVB"],["BVH"],["BWE"],["BVS"],["C4G"],["C69"],["CDC"],["CEO"],["CII"],["CRC"],["CMG"],["CRE"],["CSV"],["CTD"],["CTF"],["CTG"],["CTI"],["CTR"],["CTS"],["DBC"],["DC4"],["DDB"],["DCM"],["DCL"],["DDV"],["DGC"],["DGW"],["DHC"],["DHA"],["DL1"],["DIG"],["DLG"],["DPG"],["DPM"],["DRI"],["DSE"],["DPR"],["DTD"],["DXG"],["DXS"],["DXP"],["EIB"],["ELC"],["EVF"],["EVG"],["FCN"],["FIT"],["FOX"],["FRT"],["FPT"],["FTS"],["G36"],["GDA"],["GEE"],["GAS"],["GEG"],["GEX"],["GVR"],["GMD"],["HAG"],["HAH"],["HAX"],["HBC"],["HCM"],["HDB"],["HDC"],["HHP"],["HDG"],["HHS"],["HHV"],["HID"],["HII"],["HNG"],["HPX"],["HPG"],["HQC"],["HSL"],["HSG"],["HT1"],["HUT"],["HVN"],["IDC"],["IDI"],["IJC"],["IPA"],["IMP"],["KBC"],["KDC"],["KDH"],["KHG"],["KLB"],["KOS"],["KSV"],["KSB"],["L40"],["LCG"],["LDG"],["LPB"],["LGL"],["LSG"],["MBB"],["MBS"],["MCH"],["MIG"],["MML"],["MSB"],["MSH"],["MZG"],["MSN"],["MSR"],["MST"],["NAB"],["MWG"],["NAF"],["NHH"],["NKG"],["NLG"],["NRC"],["NNC"],["NTC"],["NT2"],["NTL"],["NTP"],["NVL"],["OCB"],["OIL"],["ORS"],["PAT"],["PAC"],["PAN"],["PC1"],["PDR"],["PET"],["PHR"],["PIV"],["PLP"],["PLX"],["PNJ"],["PPT"],["POW"],["PSD"],["PTB"],["PVC"],["PVP"],["PVD"],["PVI"],["PVS"],["PVT"],["QNS"],["QCG"],["SBG"],["SAB"],["REE"],["SBS"],["SBT"],["SCS"],["SCR"],["SGP"],["SGR"],["SHB"],["SHI"],["SIP"],["SHS"],["SSB"],["SJE"],["SMC"],["SSI"],["SZC"],["TAL"],["STB"],["TCB"],["TCH"],["TCX"],["TCM"],["TDP"],["TIG"],["TOS"],["TLG"],["TNG"],["TPB"],["TRC"],["TSC"],["TTN"],["TTF"],["VAB"],["TV2"],["VC3"],["VCK"],["VCB"],["VCI"],["VCG"],["VCS"],["VEA"],["VEC"],["VDS"],["VFS"],["VGC"],["VGI"],["VGT"],["VGS"],["VHM"],["VHC"],["VIB"],["VIC"],["VJC"],["VIX"],["VNB"],["VND"],["VNP"],["VNM"],["VOS"],["VPB"],["VPL"],["VPI"],["VPX"],["VRE"],["VTZ"],["VTP"],["VVS"],["VSC"],["YEG"]
# ]
# fmt: on

# lấy 3 năm gần nhất để đồng bộ dữ liệu và thời điểm tính toán các chỉ số
START_DATE = (date.today() - relativedelta(years=3)).strftime("%Y-%m-%d")
CHART_START_DATE = '2025-03-23'

lstTicker = [["MZG"]]

# --- SYSTEM & ENVIRONMENT CONFIGURATION ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Base Datafile Folder path resolved from environment variables
PROJECT_FOLDER = Path(__file__).parent.parent.resolve()
DATAFILE_FOLDER = os.getenv("DATAFILE_FOLDER", os.getenv("OneDrive", "C:\\") + "\\Datafile\\")  # type: ignore

# DuckDB Database File Paths
LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", os.path.join(DATAFILE_FOLDER, "CherryMon.duckdb"))
DB_PATH_CHERRYMON = LOCAL_DB_PATH
DB_MOTHERDUCK_PATH = os.getenv("DB_MOTHERDUCK_PATH", "md:CherryMon")
DB_MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN", "")
# DuckDB sql Path
DUCKDB_SQL_PATH = Path(r"C:\Github\CherryStock\DuckDB\sql")

# File exporting paths
DATAFILE_PATH = Path(r"C:\Users\ADMIN\OneDrive - ollyo\Datafile")

# Amibroker paths
AMIBROKER_LOG_PATH = Path(r"C:\Program1\AmiBroker\broker.log")
AMIBROKER_AFL_PATH = Path(r"C:\Github\CherryStock\Amibroker\Formulas\CherryMon")
AMIBROKER_EOD_PATH = Path(r"C:\Program1\AmiBroker\Data_FireAnt\AmiBroker\EOD")
AMIBROKER_EOD_ACTIVE_PATH = AMIBROKER_EOD_PATH / "active"
AMIBROKER_EOD_COMMODITY_PATH = AMIBROKER_EOD_PATH / "commodity"
AMIBROKER_EOD_FOREIGN_PATH = AMIBROKER_EOD_PATH / "foreign"
AMIBROKER_EOD_FUTURES_PATH = AMIBROKER_EOD_PATH / "futures"
AMIBROKER_EOD_INDEX_PATH = AMIBROKER_EOD_PATH / "index"
AMIBROKER_EOD_INDUSTRY_PATH = AMIBROKER_EOD_PATH / "industry"
AMIBROKER_EOD_MARKET_PATH = AMIBROKER_EOD_PATH / "market"
AMIBROKER_EOD_OTHER_PATH = AMIBROKER_EOD_PATH / "other"
AMIBROKER_EOD_PROP_PATH = AMIBROKER_EOD_PATH / "prop"
AMIBROKER_EOD_STOCK_PATH = AMIBROKER_EOD_PATH / "stock"
AMIBROKER_EOD_SUPPLYDEMAND_PATH = AMIBROKER_EOD_PATH / "supplydemand"
AMIBROKER_EOD_WARRANT_PATH = AMIBROKER_EOD_PATH / "warrant"
AMIBROKER_INTRADAY_PATH = Path(r"C:\Program1\AmiBroker\Data_FireAnt\AmiBroker\Intraday")
AMIBROKER_INTRADAY_FUTURES_PATH = AMIBROKER_INTRADAY_PATH / "futures"
AMIBROKER_INTRADAY_INDEX_PATH = AMIBROKER_INTRADAY_PATH / "index"
AMIBROKER_INTRADAY_STOCK_PATH = AMIBROKER_INTRADAY_PATH / "stock"
AMIBROKER_INTRADAY_WARRANT_PATH = AMIBROKER_INTRADAY_PATH / "warrant"

# Agent and other constants
AGENT_NAME = "CherryMonAgent"
AGENT_PATH = Path(r"C:\Github\CherryStock\.github\agents")

# WebApp Configuration
IFRAME_WIDTH = 1200
IFRAME_HEIGHT = 600
PRICE_SCALE_MIN_WIDTH = 80