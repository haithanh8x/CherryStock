import os
from pathlib import Path

# lstTicker = [
#     ["AAH"],["AAS"],["ABB"],["AAA"],["ACV"],["ACB"],["AFX"],["AGG"],["ANT"],["AGR"],["APH"],["ANV"],["BAF"],["APS"],["BCM"],["BFC"],["BIC"],["BID"],["BMI"],["BMP"],["BSI"],["BSR"],["BVB"],["BVH"],["BWE"],["BVS"],["C4G"],["C69"],["CDC"],["CEO"],["CII"],["CRC"],["CMG"],["CRE"],["CSV"],["CTD"],["CTF"],["CTG"],["CTI"],["CTR"],["CTS"],["DBC"],["DC4"],["DDB"],["DCM"],["DCL"],["DDV"],["DGC"],["DGW"],["DHC"],["DHA"],["DL1"],["DIG"],["DLG"],["DPG"],["DPM"],["DRI"],["DSE"],["DPR"],["DTD"],["DXG"],["DXS"],["DXP"],["EIB"],["ELC"],["EVF"],["EVG"],["FCN"],["FIT"],["FOX"],["FRT"],["FPT"],["FTS"],["G36"],["GDA"],["GEE"],["GAS"],["GEG"],["GEX"],["GVR"],["GMD"],["HAG"],["HAH"],["HAX"],["HBC"],["HCM"],["HDB"],["HDC"],["HHP"],["HDG"],["HHS"],["HHV"],["HID"],["HII"],["HNG"],["HPX"],["HPG"],["HQC"],["HSL"],["HSG"],["HT1"],["HUT"],["HVN"],["IDC"],["IDI"],["IJC"],["IPA"],["IMP"],["KBC"],["KDC"],["KDH"],["KHG"],["KLB"],["KOS"],["KSV"],["KSB"],["L40"],["LCG"],["LDG"],["LPB"],["LGL"],["LSG"],["MBB"],["MBS"],["MCH"],["MIG"],["MML"],["MSB"],["MSH"],["MZG"],["MSN"],["MSR"],["MST"],["NAB"],["MWG"],["NAF"],["NHH"],["NKG"],["NLG"],["NRC"],["NNC"],["NTC"],["NT2"],["NTL"],["NTP"],["NVL"],["OCB"],["OIL"],["ORS"],["PAT"],["PAC"],["PAN"],["PC1"],["PDR"],["PET"],["PHR"],["PIV"],["PLP"],["PLX"],["PNJ"],["PPT"],["POW"],["PSD"],["PTB"],["PVC"],["PVP"],["PVD"],["PVI"],["PVS"],["PVT"],["QNS"],["QCG"],["SBG"],["SAB"],["REE"],["SBS"],["SBT"],["SCS"],["SCR"],["SGP"],["SGR"],["SHB"],["SHI"],["SIP"],["SHS"],["SSB"],["SJE"],["SMC"],["SSI"],["SZC"],["TAL"],["STB"],["TCB"],["TCH"],["TCX"],["TCM"],["TDP"],["TIG"],["TOS"],["TLG"],["TNG"],["TPB"],["TRC"],["TSC"],["TTN"],["TTF"],["VAB"],["TV2"],["VC3"],["VCK"],["VCB"],["VCI"],["VCG"],["VCS"],["VEA"],["VEC"],["VDS"],["VFS"],["VGC"],["VGI"],["VGT"],["VGS"],["VHM"],["VHC"],["VIB"],["VIC"],["VJC"],["VIX"],["VNB"],["VND"],["VNP"],["VNM"],["VOS"],["VPB"],["VPL"],["VPI"],["VPX"],["VRE"],["VTZ"],["VTP"],["VVS"],["VSC"],["YEG"]
# ]
lstTicker = [ ["MZG"] ]

var_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                    "AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/120.0.0.0 Safari/537.36"
var_Datafile_Folder = os.getenv("OneDrive", "C:\\") + "\\Datafile\\" # type: ignore

db_path_CherryMon = os.path.join(var_Datafile_Folder, "CherryMon.duckdb")

# Global project path
DATAFILE_PATH = Path(r"C:\Users\ADMIN\OneDrive - ollyo\Datafile")