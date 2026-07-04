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