-- CherryStock industry indices. Additive schema; no mutation of source facts.
-- All prices are adjusted analytical prices in thousand VND / share.
-- Index close is a dimensionless level (base 1000), not a price in VND.

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_Industry_Index_D" (
    "Date" DATE NOT NULL,
    "IndustryCode" VARCHAR NOT NULL,
    "Industry" VARCHAR,
    "Index_Method" VARCHAR NOT NULL,
    "Close" DOUBLE NOT NULL,
    "Daily_Return" DOUBLE NOT NULL,
    "Pct_Change" DOUBLE NOT NULL,
    "Volume" BIGINT,
    "TradingValue" HUGEINT,
    "TradingValue_Known_Count" INTEGER NOT NULL,
    "TradingValue_Proxy_Count" INTEGER NOT NULL,
    "Ticker_Count" INTEGER NOT NULL,
    "Advancers" INTEGER NOT NULL,
    "Decliners" INTEGER NOT NULL,
    "Unchanged" INTEGER NOT NULL,
    "FloatMarketCap_ThousandVND" DOUBLE,
    "Max_Weight" DOUBLE NOT NULL,
    "Top3_Weight" DOUBLE NOT NULL,
    "Calculation_Mode" VARCHAR NOT NULL,
    "Snapshot_Date" DATE NOT NULL,
    "Calculated_At" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("Date", "IndustryCode", "Index_Method"),
    CHECK ("Index_Method" IN ('FFMC', 'EW')),
    CHECK ("Close" > 0)
);

CREATE TABLE IF NOT EXISTS "CherryMon"."main"."cal_Industry_Index_Weights" (
    "Date" DATE NOT NULL,
    "IndustryCode" VARCHAR NOT NULL,
    "Index_Method" VARCHAR NOT NULL,
    "Ticker" VARCHAR NOT NULL,
    "Close" DOUBLE NOT NULL,
    "Previous_Close" DOUBLE NOT NULL,
    "FloatShares" DOUBLE,
    "Weight" DOUBLE NOT NULL,
    "Return_Weight" DOUBLE NOT NULL,
    "Price_Return" DOUBLE NOT NULL,
    "Return_Contribution" DOUBLE NOT NULL,
    "Snapshot_Date" DATE NOT NULL,
    PRIMARY KEY ("Date", "IndustryCode", "Index_Method", "Ticker"),
    CHECK ("Index_Method" IN ('FFMC', 'EW')),
    CHECK ("Weight" >= 0 AND "Weight" <= 1.00000001),
    CHECK ("Return_Weight" >= 0 AND "Return_Weight" <= 1.00000001)
);

CREATE OR REPLACE VIEW "CherryMon"."main"."vw_Industry_Index_D" AS
SELECT
    "Date", "IndustryCode", "Industry", "Index_Method",
    "Close", "Daily_Return", "Pct_Change",
    "Volume", "TradingValue", "TradingValue_Known_Count",
    "TradingValue_Proxy_Count", "Ticker_Count",
    "Advancers", "Decliners", "Unchanged",
    "FloatMarketCap_ThousandVND", "Max_Weight", "Top3_Weight",
    "Calculation_Mode", "Snapshot_Date", "Calculated_At"
FROM "CherryMon"."main"."cal_Industry_Index_D";

-- Idempotent metadata comments; supported by DuckDB COMMENT ON.
COMMENT ON TABLE "CherryMon"."main"."cal_Industry_Index_D" IS 'Mỗi dòng là chỉ số ngành theo ngày và phương pháp tính; dữ liệu lịch sử sử dụng danh sách cổ phiếu và FreeFloat mới nhất, không phải dữ liệu point-in-time.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Date" IS 'Ngày giao dịch của chỉ số ngành.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."IndustryCode" IS 'Mã ngành lấy từ vw_Ticker_Info, dùng làm khóa phân nhóm.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Industry" IS 'Tên ngành dùng để hiển thị, lấy từ danh mục cổ phiếu hiện tại.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Index_Method" IS 'Phương pháp tính: FFMC theo vốn hóa free-float; EW theo trọng số bằng nhau.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Close" IS 'Điểm chỉ số ngành cuối phiên, mốc cơ sở 1000; không phải giá cổ phiếu hay số tiền.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Daily_Return" IS 'Lợi suất chỉ số trong phiên dạng số thập phân; 0.0125 tương ứng tăng 1.25%.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Pct_Change" IS 'Phần trăm thay đổi chỉ số trong phiên, bằng Daily_Return nhân 100.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Volume" IS 'Tổng khối lượng giao dịch EOD của các cổ phiếu thành phần hợp lệ, đơn vị cổ phiếu.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."TradingValue" IS 'Tổng giá trị giao dịch có dữ liệu của các cổ phiếu thành phần, đơn vị VND; có thể gồm giá trị ước tính từ EOD; NULL nếu không có dữ liệu.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."TradingValue_Known_Count" IS 'Số cổ phiếu thành phần có TradingValue khác NULL.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."TradingValue_Proxy_Count" IS 'Số cổ phiếu thành phần có TradingValue được ước tính từ giá điển hình EOD.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Ticker_Count" IS 'Số cổ phiếu hợp lệ tham gia tính chỉ số ngành theo phương pháp tương ứng.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Advancers" IS 'Số cổ phiếu thành phần có lợi suất giá đóng cửa đã điều chỉnh dương.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Decliners" IS 'Số cổ phiếu thành phần có lợi suất giá đóng cửa đã điều chỉnh âm.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Unchanged" IS 'Số cổ phiếu thành phần có lợi suất giá đóng cửa đã điều chỉnh bằng 0.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."FloatMarketCap_ThousandVND" IS 'Tổng vốn hóa free-float xấp xỉ bằng Close nhân FreeFloat mới nhất, đơn vị nghìn VND; chỉ có giá trị với FFMC.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Max_Weight" IS 'Tỷ trọng cuối phiên lớn nhất của một cổ phiếu thành phần, dạng tỷ lệ 0 đến 1.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Top3_Weight" IS 'Tổng tỷ trọng cuối phiên của ba cổ phiếu thành phần lớn nhất, dạng tỷ lệ 0 đến 1.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Calculation_Mode" IS 'Nguồn gốc phương pháp tính; HISTORICAL_PROXY_LATEST_FLOAT dùng FreeFloat và danh sách cổ phiếu hiện tại cho lịch sử.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Snapshot_Date" IS 'Ngày snapshot FreeFloat mới nhất được dùng khi tính hoặc refresh dòng dữ liệu.';
COMMENT ON COLUMN "CherryMon"."main"."cal_Industry_Index_D"."Calculated_At" IS 'Thời điểm engine ghi kết quả chỉ số vào DuckDB.';

-- Public view metadata mirrors the source table's Vietnamese descriptions.
-- Reapply after CREATE OR REPLACE VIEW, because view metadata is independent.
COMMENT ON VIEW "CherryMon"."main"."vw_Industry_Index_D" IS 'Mỗi dòng là chỉ số ngành theo ngày và phương pháp tính; dữ liệu lịch sử sử dụng danh sách cổ phiếu và FreeFloat mới nhất, không phải dữ liệu point-in-time.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Date" IS 'Ngày giao dịch của chỉ số ngành.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."IndustryCode" IS 'Mã ngành lấy từ vw_Ticker_Info, dùng làm khóa phân nhóm.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Industry" IS 'Tên ngành dùng để hiển thị, lấy từ danh mục cổ phiếu hiện tại.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Index_Method" IS 'Phương pháp tính: FFMC theo vốn hóa free-float; EW theo trọng số bằng nhau.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Close" IS 'Điểm chỉ số ngành cuối phiên, mốc cơ sở 1000; không phải giá cổ phiếu hay số tiền.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Daily_Return" IS 'Lợi suất chỉ số trong phiên dạng số thập phân; 0.0125 tương ứng tăng 1.25%.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Pct_Change" IS 'Phần trăm thay đổi chỉ số trong phiên, bằng Daily_Return nhân 100.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Volume" IS 'Tổng khối lượng giao dịch EOD của các cổ phiếu thành phần hợp lệ, đơn vị cổ phiếu.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."TradingValue" IS 'Tổng giá trị giao dịch có dữ liệu của các cổ phiếu thành phần, đơn vị VND; có thể gồm giá trị ước tính từ EOD; NULL nếu không có dữ liệu.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."TradingValue_Known_Count" IS 'Số cổ phiếu thành phần có TradingValue khác NULL.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."TradingValue_Proxy_Count" IS 'Số cổ phiếu thành phần có TradingValue được ước tính từ giá điển hình EOD.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Ticker_Count" IS 'Số cổ phiếu hợp lệ tham gia tính chỉ số ngành theo phương pháp tương ứng.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Advancers" IS 'Số cổ phiếu thành phần có lợi suất giá đóng cửa đã điều chỉnh dương.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Decliners" IS 'Số cổ phiếu thành phần có lợi suất giá đóng cửa đã điều chỉnh âm.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Unchanged" IS 'Số cổ phiếu thành phần có lợi suất giá đóng cửa đã điều chỉnh bằng 0.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."FloatMarketCap_ThousandVND" IS 'Tổng vốn hóa free-float xấp xỉ bằng Close nhân FreeFloat mới nhất, đơn vị nghìn VND; chỉ có giá trị với FFMC.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Max_Weight" IS 'Tỷ trọng cuối phiên lớn nhất của một cổ phiếu thành phần, dạng tỷ lệ 0 đến 1.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Top3_Weight" IS 'Tổng tỷ trọng cuối phiên của ba cổ phiếu thành phần lớn nhất, dạng tỷ lệ 0 đến 1.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Calculation_Mode" IS 'Nguồn gốc phương pháp tính; HISTORICAL_PROXY_LATEST_FLOAT dùng FreeFloat và danh sách cổ phiếu hiện tại cho lịch sử.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Snapshot_Date" IS 'Ngày snapshot FreeFloat mới nhất được dùng khi tính hoặc refresh dòng dữ liệu.';
COMMENT ON COLUMN "CherryMon"."main"."vw_Industry_Index_D"."Calculated_At" IS 'Thời điểm engine ghi kết quả chỉ số vào DuckDB.';
