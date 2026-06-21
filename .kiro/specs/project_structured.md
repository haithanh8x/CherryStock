# Cấu trúc thư mục của dự án CherryStock
- CherryMon Arch.drawio file kiến trúc hệ thống

## CrawlStock ingest data từ nhiều data sources khác nhau
    - lstDuckDB.py insert data vào DuckDB theo cơ chế upsert

## Amibroker lưu các script thực thi của Amibroker
### Batch lưu các file thực thi Amiroker Script
    - ALL_Shares.abb: Batch script that runs 4 AmiBroker analysis projects sequentially
    - ALL_Shares.bat: Windows batch launcher
    - ALL_Shares.vbs: VBScript orchestrator that invokes AmiBroker batch mode
    - ALL_Shares.apx: Analysis project (for stock fundamentals/metrics) exports *All_Shares.csv* (stock metrics & indicators) lấy từ *Export Data.afl*
    The formula calculates technical indicators:
    RSI (14-day base, weekly, monthly)
    TSI (Total Strength Index)
    ATR percentage
    Moving averages (MA5, MA20)
    Price channels (1W, 1M, 3M, 6M, 1Y, 5Y highs/lows)
    MACD signals
    Slope angles (20, 50, 150, 250, 1250 days)
    Volume conditions (5 consecutive days above 5000)
    Filtered for symbols with 5+ days of sustained volume above 5000.

    - ALL_Shares_TimeSeries.apx	Analysis project (for time series data) exports *ALL_Shares_TimeSeries.csv*(historical prices)
    - ThongKe.apx → exports *ThongKe.csv* (statistical summary)
    - Ticker_Attr.apx → exports *Ticker_Attr.csv* (ticker attributes)

### Formulas lưu các file ALF code, thư viện
    - ALL_Shares.apx: liệt kê toàn bộ cổ phiếu ticker trong một ngày về Technical Analysis
    - Intraday ACCCNNTD.apx: liệt kê các thông tin về giao dịch chủ động, mua bán nước ngoài và tự doanh

## DuckDB database lưu thông tin stock

## Telegram nhắn tin và notification
- KieuNuDaiGia_Funds nhắn tin vào kênh *Manhattan Channel*