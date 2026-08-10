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
from pathlib import Path

from dateutil.relativedelta import relativedelta
from cherrystock.config.settings import settings

# --- TICKER CONFIGURATION ---
# Full ticker list preserved for future reference
# fmt: off
# lstTicker = [
#     ["AAH"],["AAS"],["ABB"],["AAA"],["ACV"],["ACB"],["AFX"],["AGG"],["ANT"],["AGR"],["APH"],["ANV"],["BAF"],["APS"],["BCM"],["BFC"],["BIC"],["BID"],["BMI"],["BMP"],["BSI"],["BSR"],["BVB"],["BVH"],["BWE"],["BVS"],["C4G"],["C69"],["CDC"],["CEO"],["CII"],["CRC"],["CMG"],["CRE"],["CSV"],["CTD"],["CTF"],["CTG"],["CTI"],["CTR"],["CTS"],["DBC"],["DC4"],["DDB"],["DCM"],["DCL"],["DDV"],["DGC"],["DGW"],["DHC"],["DHA"],["DL1"],["DIG"],["DLG"],["DPG"],["DPM"],["DRI"],["DSE"],["DPR"],["DTD"],["DXG"],["DXS"],["DXP"],["EIB"],["ELC"],["EVF"],["EVG"],["FCN"],["FIT"],["FOX"],["FRT"],["FPT"],["FTS"],["G36"],["GDA"],["GEE"],["GAS"],["GEG"],["GEX"],["GVR"],["GMD"],["HAG"],["HAH"],["HAX"],["HBC"],["HCM"],["HDB"],["HDC"],["HHP"],["HDG"],["HHS"],["HHV"],["HID"],["HII"],["HNG"],["HPX"],["HPG"],["HQC"],["HSL"],["HSG"],["HT1"],["HUT"],["HVN"],["IDC"],["IDI"],["IJC"],["IPA"],["IMP"],["KBC"],["KDC"],["KDH"],["KHG"],["KLB"],["KOS"],["KSV"],["KSB"],["L40"],["LCG"],["LDG"],["LPB"],["LGL"],["LSG"],["MBB"],["MBS"],["MCH"],["MIG"],["MML"],["MSB"],["MSH"],["MZG"],["MSN"],["MSR"],["MST"],["NAB"],["MWG"],["NAF"],["NHH"],["NKG"],["NLG"],["NRC"],["NNC"],["NTC"],["NT2"],["NTL"],["NTP"],["NVL"],["OCB"],["OIL"],["ORS"],["PAT"],["PAC"],["PAN"],["PC1"],["PDR"],["PET"],["PHR"],["PIV"],["PLP"],["PLX"],["PNJ"],["PPT"],["POW"],["PSD"],["PTB"],["PVC"],["PVP"],["PVD"],["PVI"],["PVS"],["PVT"],["QNS"],["QCG"],["SBG"],["SAB"],["REE"],["SBS"],["SBT"],["SCS"],["SCR"],["SGP"],["SGR"],["SHB"],["SHI"],["SIP"],["SHS"],["SSB"],["SJE"],["SMC"],["SSI"],["SZC"],["TAL"],["STB"],["TCB"],["TCH"],["TCX"],["TCM"],["TDP"],["TIG"],["TOS"],["TLG"],["TNG"],["TPB"],["TRC"],["TSC"],["TTN"],["TTF"],["VAB"],["TV2"],["VC3"],["VCK"],["VCB"],["VCI"],["VCG"],["VCS"],["VEA"],["VEC"],["VDS"],["VFS"],["VGC"],["VGI"],["VGT"],["VGS"],["VHM"],["VHC"],["VIB"],["VIC"],["VJC"],["VIX"],["VNB"],["VND"],["VNP"],["VNM"],["VOS"],["VPB"],["VPL"],["VPI"],["VPX"],["VRE"],["VTZ"],["VTP"],["VVS"],["VSC"],["YEG"]
# ]
# fmt: on

# lấy 3 năm gần nhất để đồng bộ dữ liệu và thời điểm tính toán các chỉ số
START_DATE = (date.today() - relativedelta(years=3)).strftime("%Y-%m-%d")
CHART_START_DATE = '2024-04-01'

lstTicker = [["MZG"]]

# --- SYSTEM & ENVIRONMENT CONFIGURATION ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Base Datafile Folder path resolved from environment variables
PROJECT_FOLDER = settings.src_root
DATAFILE_FOLDER = settings.datafile_folder

# DuckDB Database File Paths
LOCAL_DB_PATH = str(settings.local_db_path)
DB_PATH_CHERRYMON = LOCAL_DB_PATH
DB_MOTHERDUCK_PATH = settings.motherduck_path or "md:CherryMon"
DB_MOTHERDUCK_TOKEN = settings.motherduck_token or ""
# DuckDB sql Path
DUCKDB_SQL_PATH = settings.duckdb_sql_path

# File exporting paths
DATAFILE_PATH = settings.datafile_path

# Amibroker paths
AMIBROKER_ROOT = settings.amibroker_root
AMIBROKER_LOG_PATH = settings.amibroker_log_path
AMIBROKER_AFL_PATH = settings.amibroker_afl_path
AMIBROKER_EOD_PATH = settings.amibroker_eod_path
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
AMIBROKER_INTRADAY_PATH = settings.amibroker_intraday_path
AMIBROKER_INTRADAY_FUTURES_PATH = AMIBROKER_INTRADAY_PATH / "futures"
AMIBROKER_INTRADAY_INDEX_PATH = AMIBROKER_INTRADAY_PATH / "index"
AMIBROKER_INTRADAY_STOCK_PATH = AMIBROKER_INTRADAY_PATH / "stock"
AMIBROKER_INTRADAY_WARRANT_PATH = AMIBROKER_INTRADAY_PATH / "warrant"

# Agent and other constants
AGENT_NAME = "CherryMonAgent"
AGENT_PATH = settings.agent_path

# WebApp Configuration
IFRAME_WIDTH = 1200
IFRAME_HEIGHT = 600
PRICE_SCALE_MIN_WIDTH = 80
TIMEFRAME_OPTIONS = {
    "daily": "Ngày",
    "weekly": "Tuần",
    "monthly": "Tháng",
}
THEME = {
    "background": "#07111f",
    "surface": "#0f1b2d",
    "surface_alt": "#14233a",
    "border": "#263750",
    "text": "#e5edf7",
    "muted": "#8fa3bd",
    "primary": "#38bdf8",
    "positive": "#22c55e",
    "negative": "#ef4444",
    "warning": "#f59e0b",
}