from typing import Optional, Dict
import pandas as pd
from Ults.DuckLib import DuckDBManager

def get_symbol(
    index_name: str,
    start_date: str = "2025-01-01",
    columns_mapping: Optional[Dict[str, str]] = None,
    source: str = "stock"
) -> pd.DataFrame:
    """
    Lấy và chuẩn hóa dữ liệu chỉ số theo nguồn dữ liệu được chọn.
    
    :param index_name: Tên mã/chỉ số cần lọc.
    :param start_date: Ngày bắt đầu lọc dữ liệu (định dạng 'YYYY-MM-DD')
    :param columns_mapping: Dictionary cấu hình tên cột gốc và Alias cần lấy.
                            Mặc định nếu None sẽ lấy: {"Date": "time", "Close": "Y"}
    :param source: Nguồn dữ liệu, hỗ trợ: 'stock'/'index' -> raw_index_eod, 'custom' -> cal_Indexes.
    :return: DataFrame đã được xử lý chuẩn hóa sẵn sàng cho Chart.
    """
    if columns_mapping is None:
        columns_mapping = {"Date": "time", "Close": "Y"}

    source_key = source.lower().strip()
    source_config = {
        "stock": ('"CherryMon"."main"."raw_stock_eod"', '"Ticker"'),
        "index": ('"CherryMon"."main"."raw_index_eod"', '"Ticker"'),
        "other": ('"CherryMon"."main"."raw_other_eod"', '"Ticker"'),
        "custom": ('"CherryMon"."main"."cal_Indexes"', '"Index_Name"'),
    }
    if source_key not in source_config:
        raise ValueError("source must be one of: 'stock', 'index', 'custom'")

    table_name, symbol_col = source_config[source_key]
        
    select_parts = [f'w."{col}" AS {alias}' for col, alias in columns_mapping.items()]
    select_clause = ", ".join(select_parts)
    
    sql = f'''
    SELECT
        {select_clause}
    FROM {table_name} w
    WHERE w.{symbol_col} = ?
      AND w."Date" >= ?
    ORDER BY w."Date" DESC
    '''
    
    with DuckDBManager() as con:
        relation = con.sql(sql, params=[index_name, start_date])
        df = relation.df()
        
    if df.empty:
        return pd.DataFrame(columns=list(columns_mapping.values()))
        
    time_col = columns_mapping.get("Date", "time")
    
    df[time_col] = (
        pd.to_datetime(df[time_col], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    df = df.sort_values(time_col).reset_index(drop=True)
    df[time_col] = df[time_col].dt.strftime("%Y-%m-%d")
    
    return df.loc[:, list(columns_mapping.values())]

def upd_symbol_percent(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    
    # Lấy giá trị Y của ngày đầu tiên (ngày cũ nhất trong chuỗi sau khi đã sort)
    first_value = df["Y"].iloc[0]
    
    # Tính toán tỷ lệ %: ((Giá hôm nay - Giá ngày đầu) / Giá ngày đầu) * 100
    df["Y"] = ((df["Y"] - first_value) / first_value) * 100
    
    return df

def _normalize_time(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out['time'] = pd.to_datetime(out['time'], errors='coerce').dt.strftime('%Y-%m-%d')
    out = out.dropna(subset=['time'])
    out = out.sort_values('time').drop_duplicates(subset=['time'], keep='last').reset_index(drop=True)
    return out


def _align_to_base_time(base_time_df: pd.DataFrame, source_df: pd.DataFrame) -> pd.DataFrame:
    value_columns = [c for c in source_df.columns if c != 'time']
    if not value_columns:
        raise ValueError('DataFrame nguồn không có cột dữ liệu ngoài cột time.')

    value_col = value_columns[0]
    source_clean = _normalize_time(source_df)[['time', value_col]]
    aligned = base_time_df[['time']].merge(source_clean, on='time', how='left')
    aligned[value_col] = aligned[value_col].ffill().bfill()
    return aligned.rename(columns={value_col: 'Y'})