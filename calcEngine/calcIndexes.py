from Ults.Timing import timeit, toggle_print
from lstPara import START_DATE

def calculate_composite_index(
      current_data
    , previous_data=None
    , prev_divisor=None
    , base_value=100
):
    """Tính toán Chỉ số tổng hợp (Composite Index) theo phương pháp vốn hóa trọng số.

    Parameters:
    -----------
    current_data : pandas.DataFrame
        Dữ liệu phiên hiện tại. Bắt buộc có các cột:
        - 'ticker': Mã cổ phiếu (String)
        - 'price': Giá đóng cửa phiên hiện tại (Float)
        - 'shares': Số lượng cổ phiếu lưu hành/free-float phiên hiện tại (Float)
    previous_data : pandas.DataFrame, optional
        Dữ liệu của phiên ngay trước đó (cùng cấu trúc với current_data).
        Cần thiết nếu có sự thay đổi danh mục (thêm/bớt ticker, chia tách...) để
        tính lại Divisor.
    prev_divisor : float, optional
        Hệ số chia (Divisor) của phiên ngay trước đó.
    base_value : float, default 100
        Giá trị gốc của chỉ số tại ngày khởi tạo.

    Returns:
    --------
    index_value : float
        Giá trị chỉ số của phiên hiện tại.
    current_divisor : float
        Hệ số chia của phiên hiện tại (cần lưu lại để truyền vào phiên sau).
    """
    # 1. Tính tổng vốn hóa thị trường hiện tại
    current_data["market_cap"] = current_data["price"] * current_data["shares"]
    total_current_mcap = current_data["market_cap"].sum()

    # Trường hợp 1: Ngày khởi tạo chỉ số (Không có dữ liệu quá khứ hoặc không có divisor cũ)
    if previous_data is None or prev_divisor is None:
        current_divisor = total_current_mcap / base_value
        index_value = base_value
        return index_value, current_divisor

    # 2. Xử lý trường hợp có dữ liệu quá khứ (Tính toán biến động danh mục)
    previous_data["market_cap"] = (
        previous_data["price"] * previous_data["shares"]
    )

    # Kiểm tra xem danh sách ticker hoặc số lượng shares có bị thay đổi không
    # Bằng cách so sánh tập hợp (ticker, shares) giữa 2 phiên
    curr_structure = set(zip(current_data["ticker"], current_data["shares"]))
    prev_structure = set(zip(previous_data["ticker"], previous_data["shares"]))

    if curr_structure == prev_structure:
        # Cơ cấu danh mục không đổi -> Giữ nguyên hệ số chia cũ
        current_divisor = prev_divisor
    else:
        # Cơ cấu danh mục THAY ĐỔI (Thêm/bớt mã, hoặc chia tách cổ phiếu)
        # Bước A: Tính toán giá trị của chỉ số ngay trước khi thay đổi dựa trên giá cũ
        total_prev_mcap = previous_data["market_cap"].sum()
        prev_index_value = total_prev_mcap / prev_divisor

        # Bước B: Tính vốn hóa của danh mục MỚI nhưng sử dụng GIÁ CŨ (để cô lập biến động cơ cấu)
        # Tạo bản đồ giá cũ của từng ticker
        price_lookup = previous_data.set_index("ticker")["price"].to_dict()

        # Tính toán vốn hóa mới dựa trên giá cũ (nếu ticker mới hoàn toàn không có giá cũ, mặc định lấy giá hiện tại)
        mcap_new_structure_old_price = 0
        for _, row in current_data.iterrows():
            ticker = row["ticker"]
            shares = row["shares"]
            old_price = price_lookup.get(ticker, row["price"])
            mcap_new_structure_old_price += old_price * shares

        # Bước C: Điều chỉnh Divisor mới để chỉ số không bị nhảy vọt do thay đổi cơ cấu
        current_divisor = mcap_new_structure_old_price / prev_index_value

    # 3. Tính giá trị chỉ số cuối cùng cho phiên hiện tại
    index_value = total_current_mcap / current_divisor

    return round(index_value, 2), round(current_divisor, 2)

@timeit
@toggle_print(allow_print=False)
def calculate_VNINDEX_NOT_VIN():
    import pandas as pd
    from Ults.DuckLib import DuckDBManager
    from calcEngine.calcIndexes import calculate_composite_index
    from Ults.Timing import get_nearest_working_date

    # 1. Tính base value và dataframe cần tính composite index
    str_from_date = START_DATE
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
        (
            con.from_df(pd.DataFrame(results))
            .project(f"'{index_name}' AS INDEX_NAME, Close, Date")
            .insert_into(table_name)
        )