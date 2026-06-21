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

import os
from pathlib import Path

import duckdb

# --- TICKER CONFIGURATION ---
# Full ticker list preserved for future reference
# fmt: off
# lstTicker = [
#     ["AAH"],["AAS"],["ABB"],["AAA"],["ACV"],["ACB"],["AFX"],["AGG"],["ANT"],["AGR"],["APH"],["ANV"],["BAF"],["APS"],["BCM"],["BFC"],["BIC"],["BID"],["BMI"],["BMP"],["BSI"],["BSR"],["BVB"],["BVH"],["BWE"],["BVS"],["C4G"],["C69"],["CDC"],["CEO"],["CII"],["CRC"],["CMG"],["CRE"],["CSV"],["CTD"],["CTF"],["CTG"],["CTI"],["CTR"],["CTS"],["DBC"],["DC4"],["DDB"],["DCM"],["DCL"],["DDV"],["DGC"],["DGW"],["DHC"],["DHA"],["DL1"],["DIG"],["DLG"],["DPG"],["DPM"],["DRI"],["DSE"],["DPR"],["DTD"],["DXG"],["DXS"],["DXP"],["EIB"],["ELC"],["EVF"],["EVG"],["FCN"],["FIT"],["FOX"],["FRT"],["FPT"],["FTS"],["G36"],["GDA"],["GEE"],["GAS"],["GEG"],["GEX"],["GVR"],["GMD"],["HAG"],["HAH"],["HAX"],["HBC"],["HCM"],["HDB"],["HDC"],["HHP"],["HDG"],["HHS"],["HHV"],["HID"],["HII"],["HNG"],["HPX"],["HPG"],["HQC"],["HSL"],["HSG"],["HT1"],["HUT"],["HVN"],["IDC"],["IDI"],["IJC"],["IPA"],["IMP"],["KBC"],["KDC"],["KDH"],["KHG"],["KLB"],["KOS"],["KSV"],["KSB"],["L40"],["LCG"],["LDG"],["LPB"],["LGL"],["LSG"],["MBB"],["MBS"],["MCH"],["MIG"],["MML"],["MSB"],["MSH"],["MZG"],["MSN"],["MSR"],["MST"],["NAB"],["MWG"],["NAF"],["NHH"],["NKG"],["NLG"],["NRC"],["NNC"],["NTC"],["NT2"],["NTL"],["NTP"],["NVL"],["OCB"],["OIL"],["ORS"],["PAT"],["PAC"],["PAN"],["PC1"],["PDR"],["PET"],["PHR"],["PIV"],["PLP"],["PLX"],["PNJ"],["PPT"],["POW"],["PSD"],["PTB"],["PVC"],["PVP"],["PVD"],["PVI"],["PVS"],["PVT"],["QNS"],["QCG"],["SBG"],["SAB"],["REE"],["SBS"],["SBT"],["SCS"],["SCR"],["SGP"],["SGR"],["SHB"],["SHI"],["SIP"],["SHS"],["SSB"],["SJE"],["SMC"],["SSI"],["SZC"],["TAL"],["STB"],["TCB"],["TCH"],["TCX"],["TCM"],["TDP"],["TIG"],["TOS"],["TLG"],["TNG"],["TPB"],["TRC"],["TSC"],["TTN"],["TTF"],["VAB"],["TV2"],["VC3"],["VCK"],["VCB"],["VCI"],["VCG"],["VCS"],["VEA"],["VEC"],["VDS"],["VFS"],["VGC"],["VGI"],["VGT"],["VGS"],["VHM"],["VHC"],["VIB"],["VIC"],["VJC"],["VIX"],["VNB"],["VND"],["VNP"],["VNM"],["VOS"],["VPB"],["VPL"],["VPI"],["VPX"],["VRE"],["VTZ"],["VTP"],["VVS"],["VSC"],["YEG"]
# ]
# fmt: on

lstTicker = [["MZG"]]

# --- SYSTEM & ENVIRONMENT CONFIGURATION ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Base Datafile Folder path resolved from environment variables
PROJECT_FOLDER = Path(__file__).parent.parent.resolve()
DATAFILE_FOLDER = os.getenv("OneDrive", "C:\\") + "\\Datafile\\"  # type: ignore

# DuckDB Database File Paths
DB_PATH_CHERRYMON = os.path.join(DATAFILE_FOLDER, "CherryMon.duckdb")
DB_MOTHERDUCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImhhaXRoYW5oOHhAZ21haWwuY29tIiwibWRSZWdpb24iOiJhd3MtdXMtZWFzdC0xIiwic2Vzc2lvbiI6ImhhaXRoYW5oOHguZ21haWwuY29tIiwicGF0IjoiYzJTb0RrbXVSY0lBN1pDMHlrdkNEWVhtVzJ5SldSM0gtRy1ZT0o3aTBYWSIsInVzZXJJZCI6IjkzOGMwMjgzLWU4NjAtNGVhNC1iNGQwLTVlNzdiYjgwOWIwOSIsImlzcyI6Im1kX3BhdCIsInJlYWRPbmx5IjpmYWxzZSwidG9rZW5UeXBlIjoicmVhZF93cml0ZSIsImlhdCI6MTc4MjAyMzUzOH0.bOLdAJCnG_DX9lFGOIR-pNxxp8hY8sJw3-q8Yr1_lMM"
DB_MOTHERDUCK_PATH = "md:CherryMon"

# File exporting paths
DATAFILE_PATH = Path(r"C:\Users\ADMIN\OneDrive - ollyo\Datafile")

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


def getCherryMon_motherDuck() -> duckdb.DuckDBPyConnection:
    """ Khởi tạo và trả về kết nối tới MotherDuck """
    return duckdb.connect(
        database=DB_MOTHERDUCK_PATH, 
        config={"motherduck_token": DB_MOTHERDUCK_TOKEN}
    )

def getCherryMon_local() -> duckdb.DuckDBPyConnection:
    """ Khởi tạo và trả về kết nối tới cơ sở dữ liệu cục bộ """
    return duckdb.connect(
        database=DB_PATH_CHERRYMON
    )