# Project: CherryStock
- “Read repository instructions first”
- “Follow project conventions before editing”
- StockTerm.md định nghia các thuật ngữ liên quan đến cổ phiếu, ví dụ: EOD, FA, Index, NetVol, NetVal, v.v.
- \Datafile folder chứa các file dữ liệu từ các nguồn khác nhau về định dạng chuẩn để lưu vào DuckDB. Các file dữ liệu này có thể là CSV, Excel, JSON, v.v.
- \Amibroker folder chứa các file dữ liệu từ Amibroker script, thực hiện explore, analysis, backtest và AFL
- \calcEngine folder chứa các module tính toán các chỉ số composite index, net flow, v.v. từ dữ liệu raw stock EOD và FA
- \Chart folder chứa các module vẽ biểu đồ từ dữ liệu raw stock EOD và FA
- \CrawlStock folder chứa các module crawl dữ liệu từ các nguồn khác nhau, ví dụ: Vietstock, Cafef, FiinPro, v.v.
- \DuckDB folder chứa các file dữ liệu DuckDB script, sql script này sẽ được thực thi để tạo ra các bảng dữ liệu trong DuckDB. Các bảng dữ liệu này sẽ được sử dụng bởi các module khác trong dự án.
- \Orchestrator folder các script đặt lịch chạy, invoke các module khác trong dự án, ví dụ: crawl dữ liệu, tính toán composite index, v.v.
- \Telegram folder chứa các module gửi thông báo, cảnh báo, v.v. qua Telegram
- \Ults folder chứa các module tiện ích, ví dụ: DuckLib, Timing, v.v.
- runTest.py là file test các module trong dự án, ví dụ: test crawl dữ liệu, test tính toán composite index, v.v.
- run.py là file chính để chạy các module trong dự án, ví dụ: crawl dữ liệu, tính toán composite index, v.v.
 
# DuckDB connection 
1. luôn sử dụng DuckDBManager.get_connection() và DuckDBManager.close_connection() để open và đóng kết nối với DuckDB. Không sử dụng trực tiếp DuckDB.connect() hoặc DuckDB.close() để tránh rò rỉ kết nối.
2. viết sql query luôn viết rõ ràng tên các fields, tránh sử dụng * để select tất cả các fields
3. sử dụng DuckLib.executeDuckSQL() để thực thi các câu lệnh SQL, không sử dụng trực tiếp DuckDB.execute() để tránh rò rỉ kết nối.
4. sử dụng DuckLib.returnSQL() để thực thi các câu lệnh SQL và trả về kết quả, không sử dụng trực tiếp DuckDB.execute() để tránh rò rỉ kết nối.

# Python
1. Timing.get_nearest_working_date() Hàm này sẽ nhận vào một ngày và trả về ngày làm việc gần nhất (không phải thứ 7, chủ nhật hoặc ngày lễ). Nếu ngày được truyền vào là ngày làm việc, nó sẽ trả về chính ngày đó. Nếu không, nó sẽ tìm ngày làm việc gần nhất trước hoặc sau ngày đó.
2. khi sử dụng data trong DuckDB cần tạo kết nối, sử dụng cấu trúc, theo ví dụ như sau
  def function_name()
    with DuckDBManager() as con:
      relation = (
        <API>
      )
      df = relation.df()   

# DuckDB CherryStock database
1. "CherryMon"."main"."raw_stock_eod" - Bảng chứa dữ liệu giá đóng cửa hàng ngày của các cổ phiếu
2. "CherryMon"."main"."raw_stock_fa" - Bảng chứa dữ liệu cơ bản của các cổ phiếu
3. "CherryMon"."main"."dimCalendar" - Bảng chứa thông tin lịch làm việc
4. "CherryMon"."main"."raw_stock_index" - Bảng chứa dữ liệu chỉ số composite của các cổ phiếu
5. "CherryMon"."main"."vw_ACCCNNTD_Price" - Bảng chứa dữ liệu hàng ngày của các cổ phiếu net dòng tiền và khối lượng
  - AC_NetVol, AC_NetVal: khối lượng và gia trị ròng của các cổ phiếu trong ngày giao dịch chủ động (chủ động mua hoặc bán thể hiện mua đuổi hoặc bán bất chấp)
  - NN_NetVol, NN_NetVal: khối lượng và giá trị ròng của các cổ phiếu trong ngày của giao dịch nhà đầu tư nước ngoài
  - TD_NetVol, TD_NetVal: khối lượng và giá trị ròng của các cổ phiếu trong ngày của giao dịch tổ chức tự doanh
  - CC_NetVol, CC_NetVal: khối lượng và giá trị ròng của các cổ phiếu trong ngày của giao dịch cung cầu