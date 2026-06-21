#%%
from datetime import datetime, timedelta
import pandas as pd
from CrawlStock.readAmi import read_amibroker_dat

df = read_amibroker_dat(r"C:\Program1\AmiBroker\Data_FireAnt\AmiBroker\EOD\stock\MWG.dat")
if df is None: raise ValueError("read_amibroker_dat returned no data")
df_sorted = df.sort_values(by="Date").reset_index(drop=True)
if df_sorted.empty: raise ValueError("read_amibroker_dat returned no data")
df_first_last = pd.concat([df_sorted.head(1), df_sorted.tail(1)])
print(df_first_last)
# %%
import duckdb
from lstPara import DB_MOTHERDUCK_PATH, DB_MOTHERDUCK_TOKEN
con = duckdb.connect(
    database=DB_MOTHERDUCK_PATH, 
    config={"motherduck_token": DB_MOTHERDUCK_TOKEN}
)
try:
    # Giờ đây bạn có thể thoải mái thực hiện các lệnh quản trị:
    print("🔥 Đang thực hiện xóa bảng cũ nếu có...")
    con.execute("DROP TABLE IF EXISTS main.raw_stock_eod;")
    
    print(" Đang tạo lại bảng mới cấu trúc sạch...")
    con.execute("""
        CREATE TABLE main.raw_stock_eod (
            Ticker VARCHAR,
            Date DATE,
            Open DOUBLE,
            High DOUBLE,
            Low DOUBLE,
            Close DOUBLE,
            Volume BIGINT,
            OpenInt DOUBLE,
            PRIMARY KEY (Ticker, Date)
        );
    """)
    print("✅ Đã hoàn thành thao tác DROP và ALTER cấu trúc trên đám mây!")

except Exception as e:
    print(f" Lỗi: {e}")
finally:
    con.close()

# %%
