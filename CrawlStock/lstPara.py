import os


lstTicker = [
    ["MWG","https://finance.vietstock.vn/MWG-ctcp-dau-tu-the-gioi-di-dong.htm?tab=BCTQ"]
]

var_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
                    "AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/120.0.0.0 Safari/537.36"

var_Datafile_Folder = os.getenv("OneDrive") + "\\Datafile\\" # type: ignore