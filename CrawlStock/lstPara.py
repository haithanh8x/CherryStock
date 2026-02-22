import os

lstTicker = [
    ["ABB"]
]

var_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                    "AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/120.0.0.0 Safari/537.36"
var_Datafile_Folder = os.getenv("OneDrive", "C:\\") + "\\Datafile\\" # type: ignore

db_path_CherryMon = os.path.join(var_Datafile_Folder, "CherryMon.duckdb")