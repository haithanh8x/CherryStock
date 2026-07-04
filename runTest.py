#%%
from matplotlib.pyplot import show
from Chart.plot import plotTicker


plotTicker("MWG", "Daily")
plotTicker("MWG", "weekly")
plotTicker("MWG", "monthly")
#%%
from Ults.getData import get_last_point
print('get_last_point:', get_last_point())

#%%
import pandas as pd
from Ults.DuckLib import DuckDBManager
from calcEngine.calcIndexes import calculate_composite_index
from Ults.Timing import get_nearest_working_date

# 1. Tính base value và dataframe cần tính composite index
str_from_date = "2025-05-01"
with DuckDBManager() as conn:
    # Lấy base_value từ VNINDEX vào ngày from_date bằng Relation API
    from_date = get_nearest_working_date(conn, from_date=pd.to_datetime(str_from_date))    
    if from_date is None: from_date = pd.to_datetime(str_from_date)
    relation = (
        conn.table('"CherryMon"."main"."raw_index_eod"')
            .filter(f"Ticker = 'VNINDEX' AND Date = '{from_date.strftime('%Y-%m-%d')}'")
            .project('Close')
            .limit(1)
    )
    df_idx = relation.df()
    if df_idx is None or df_idx.shape[0] == 0: raise ValueError(f"Không tìm thấy giá trị VNINDEX cho {from_date.strftime('%Y-%m-%d')}")
    base_value = int(df_idx['Close'].iloc[0])
    if base_value is None: base_value=1000

    # lấy dataframe
    relation = (
        conn.table('"CherryMon"."main"."raw_lstTicker"').set_alias('lt')
            .join(conn.table('"CherryMon"."main"."raw_stock_fa"').set_alias('fa'), 'lt.Ticker = fa.Ticker')
            .join(conn.table('"CherryMon"."main"."raw_stock_eod"').set_alias('eod'), 'lt.Ticker = eod.Ticker')
            .filter(f"fa.Ticker NOT IN ('VIC','VRE', 'VHM') AND eod.Date >= '{from_date.strftime('%Y-%m-%d')}'")
            .project('lt.Ticker','eod.Close','fa."Shares Float"','eod.Date')
    )
    df_all = relation.df()
    df_all.columns = ['ticker', 'price', 'shares', 'Date']
    df_all["Date"] = pd.to_datetime(df_all["Date"])
    unique_dates = sorted(df_all["Date"].unique())

previous_data = None
prev_divisor = None
results = []

# Vòng lặp tính từng ngày return results[] type list
for current_date in unique_dates:
    df_date = df_all[df_all["Date"] == current_date].copy()
    if previous_data is None:
        idx, div = calculate_composite_index(df_date, base_value=base_value)
    else:
        idx, div = calculate_composite_index(
            df_date, previous_data=previous_data, prev_divisor=prev_divisor
        )

    # Lưu kết quả vào list tạm
    results.append({
        "Close": idx,
        "Date": current_date.date()
    })
    # Cập nhật trạng thái
    previous_data = df_date.copy()
    prev_divisor = div

# insert data into table_name
index_name = "VNINDEX_NOT_VIN"
table_name = '"CherryMon"."main"."cal_Indexes"'
with DuckDBManager() as con:
    # Xóa dữ liệu cũ của INDEX_NAME='VNINDEX_NOT_VIN' trước khi insert
    con.execute(f"DELETE FROM {table_name} WHERE INDEX_NAME = '{index_name}'")
    con.from_df(pd.DataFrame(results)).select(f"'{index_name}' as INDEX_NAME", "Close", "Date").insert_into(table_name)

# %%
