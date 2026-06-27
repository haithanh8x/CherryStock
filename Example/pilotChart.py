import matplotlib.pyplot as plt
import seaborn as sns

from Ults.DuckLib import getCherryMon_local

# 1. Kích hoạt hiển thị đồ thị trong Notebook
# %matplotlib inline

# 2. Kết nối tới database DuckDB của bạn
# Thay 'path_to_your_db.db' bằng đường dẫn thực tế tới file database của bạn
con = getCherryMon_local()  # Hoặc getCherryMon_motherDuck() nếu bạn muốn kết nối tới MotherDuckDB

# 3. Chạy câu lệnh SQL và chuyển thẳng thành Pandas DataFrame bằng hàm .df()
query = """
    SELECT Date, Open, Volume 
    FROM "CherryMon"."main"."raw_stock_eod" 
    WHERE Ticker = 'MWG' 
      AND Date >= '2026-01-01'
"""
df_mwg = con.execute(query).df()

# Đóng kết nối database sau khi lấy dữ liệu xong
con.close()

# --- BƯỚC VẼ ĐỒ THỊ PHÂN PHỐI ---
# Cấu hình khung vẽ gồm 1 hàng, 2 cột
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
sns.set_theme(style="whitegrid")

# Biểu đồ 1: Phân phối Giá Mở Cửa (Open Price)
sns.histplot(
    data=df_mwg,
    x="Open",
    kde=True,
    ax=axes[0],
    color="#0066CC",  # Màu xanh cá tính, formal
    bins=20,
)
axes[0].set_title(
    "Phân Phối Giá Mở Cửa (Open Price) - MWG\n(Từ 01/05/2026)",
    fontsize=13,
    fontweight="bold",
)
axes[0].set_xlabel("Giá Mở Cửa (VND)", fontsize=11)
axes[0].set_ylabel("Số phiên (Count)", fontsize=11)

# Biểu đồ 2: Phân phối Khối Lượng Giao Dịch (Volume)
sns.histplot(
    data=df_mwg,
    x="Volume",
    kde=True,
    ax=axes[1],
    color="#FF6600",  # Màu cam tương phản trực quan
    bins=20,
    log_scale=True,  # Bật log_scale giúp phân phối Volume không bị lệch, dễ nhìn hơn
)
axes[1].set_title(
    "Phân Phối Khối Lượng Giao Dịch (Volume) - MWG\n(Từ 01/05/2026)",
    fontsize=13,
    fontweight="bold",
)
axes[1].set_xlabel("Khối Lượng Giao Dịch (Log Scale)", fontsize=11)
axes[1].set_ylabel("Số phiên (Count)", fontsize=11)

# Tối ưu khoảng cách và hiển thị
plt.tight_layout()
plt.show()