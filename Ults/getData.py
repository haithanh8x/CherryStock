from datetime import date
from Ults.DuckLib import DuckDBManager

def get_last_point():
    """
    Tính khoảng cách số ngày từ ngày dữ liệu lớn nhất của VNINDEX 
    trong bảng raw_index_eod đến ngày hiện tại.
    """
    with DuckDBManager() as con:
        relation = (
            con.table('"CherryMon"."main"."raw_index_eod"')
            .filter("Ticker = 'VNINDEX'")
            .aggregate("max(Date) AS max_date")
        )
        df = relation.df()
        
    if df is not None and not df.empty:
        max_date = df["max_date"].iloc[0]
        if max_date is None:
            return None
        if hasattr(max_date, "date"):
            max_date = max_date.date()
        return (date.today() - max_date).days
    return None