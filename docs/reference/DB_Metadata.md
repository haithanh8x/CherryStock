# DuckDB Metadata

- Generated at: 2026-09-01T09:53:19.120993+00:00
- Database file: `C:\OneDrive\Working\Datafile\CherryMon.duckdb`
- Output file: `C:\Github\CherryStock\docs\reference\DB_Metadata.md`

## AI context loading guide

Use this generated reference set in the following order:

1. Read `DB_Metadata.md` for database objects, columns, types, nullability and defaults.
2. Read `dim_indicator.csv` for indicator master definitions and runtime/library mappings.
3. Read `dim_indicator_component.csv` for multi-output component contracts.
4. Read `dim_indicator_config.csv` for executable parameter/timeframe configurations.
5. Join the three snapshots by `IndicatorCode`; use `ConfigId` for calculated-value relationships and `ComponentCode` for component relationships.

The CSV files are data snapshots generated from the same DuckDB export run. Do not infer current configuration values from the Markdown schema alone.

- Schema count: 1
- Table/view count: 36

## Schemas

- `main`

## Tables

- `main`.`cal_Indexes` (BASE TABLE)
- `main`.`cal_Trends` (BASE TABLE)
- `main`.`cal_indicator_values` (BASE TABLE)
- `main`.`dimCalendar` (BASE TABLE)
- `main`.`dim_indicator` (BASE TABLE)
- `main`.`dim_indicator_component` (BASE TABLE)
- `main`.`dim_indicator_config` (BASE TABLE)
- `main`.`raw_active_eod` (BASE TABLE)
- `main`.`raw_bctc_cdkt` (BASE TABLE)
- `main`.`raw_bctc_cstc` (BASE TABLE)
- `main`.`raw_bctc_kqkd` (BASE TABLE)
- `main`.`raw_commodity_eod` (BASE TABLE)
- `main`.`raw_foreign_eod` (BASE TABLE)
- `main`.`raw_futures_eod` (BASE TABLE)
- `main`.`raw_futures_intraday` (BASE TABLE)
- `main`.`raw_index_eod` (BASE TABLE)
- `main`.`raw_index_intraday` (BASE TABLE)
- `main`.`raw_industry_eod` (BASE TABLE)
- `main`.`raw_lstTicker` (BASE TABLE)
- `main`.`raw_market_eod` (BASE TABLE)
- `main`.`raw_other_eod` (BASE TABLE)
- `main`.`raw_prop_eod` (BASE TABLE)
- `main`.`raw_stock_eod` (BASE TABLE)
- `main`.`raw_stock_fa` (BASE TABLE)
- `main`.`raw_stock_intraday` (BASE TABLE)
- `main`.`raw_supplydemand_eod` (BASE TABLE)
- `main`.`raw_tblBCTC` (BASE TABLE)
- `main`.`raw_warrant_eod` (BASE TABLE)
- `main`.`raw_warrant_intraday` (BASE TABLE)
- `main`.`sys_data_quality_audit` (BASE TABLE)
- `main`.`t` (BASE TABLE)
- `main`.`vw_ACCCNNTD` (VIEW)
- `main`.`vw_ACCCNNTD_Price` (VIEW)
- `main`.`vw_Indicator_config` (VIEW)
- `main`.`vw_Ticker` (VIEW)
- `main`.`vw_Ticker_indicators` (VIEW)

## Objects

### main.cal_Indexes (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `INDEX_NAME` | `VARCHAR` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |

### main.cal_Trends (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `MA20` | `DOUBLE` | `YES` | `` |
| `MA50` | `DOUBLE` | `YES` | `` |
| `MA100` | `DOUBLE` | `YES` | `` |
| `MA200` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `MA20_W` | `DOUBLE` | `YES` | `` |
| `MA50_W` | `DOUBLE` | `YES` | `` |
| `MA20_M` | `DOUBLE` | `YES` | `` |
| `MA50_M` | `DOUBLE` | `YES` | `` |

### main.cal_indicator_values (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `ConfigId` | `BIGINT` | `NO` | `` |
| `ComponentCode` | `VARCHAR` | `NO` | `` |
| `Value` | `DOUBLE` | `YES` | `` |
| `CalculatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |

### main.dimCalendar (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `DateKey` | `BIGINT` | `YES` | `` |
| `FullDate` | `DATE` | `YES` | `` |
| `DayNumberOfWeek` | `BIGINT` | `YES` | `` |
| `DayNameOfWeek` | `VARCHAR` | `YES` | `` |
| `DayNumberOfMonth` | `BIGINT` | `YES` | `` |
| `DayNumberOfYear` | `BIGINT` | `YES` | `` |
| `WeekNumberOfYear` | `VARCHAR` | `YES` | `` |
| `EnglishMonthName` | `VARCHAR` | `YES` | `` |
| `MonthNumberOfYear` | `BIGINT` | `YES` | `` |
| `CalendarQuarter` | `BIGINT` | `YES` | `` |
| `QuarterName` | `VARCHAR` | `YES` | `` |
| `QuarterYear` | `VARCHAR` | `YES` | `` |
| `CalendarYear` | `BIGINT` | `YES` | `` |
| `IsHoliday` | `VARCHAR` | `YES` | `` |

### main.dim_indicator (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `IndicatorCode` | `VARCHAR` | `NO` | `` |
| `IndicatorName` | `VARCHAR` | `NO` | `` |
| `Category` | `VARCHAR` | `NO` | `` |
| `Engine` | `VARCHAR` | `NO` | `` |
| `FunctionName` | `VARCHAR` | `NO` | `` |
| `RequiredInputs` | `JSON` | `NO` | `` |
| `ParameterSchema` | `JSON` | `YES` | `` |
| `Description` | `VARCHAR` | `YES` | `` |
| `IsActive` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `YES` | `` |

### main.dim_indicator_component (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `IndicatorCode` | `VARCHAR` | `NO` | `` |
| `ComponentCode` | `VARCHAR` | `NO` | `` |
| `ComponentName` | `VARCHAR` | `NO` | `` |
| `OutputPrefix` | `VARCHAR` | `YES` | `` |
| `SortOrder` | `INTEGER` | `YES` | `` |
| `IsPrimary` | `BOOLEAN` | `NO` | `CAST('f' AS BOOLEAN)` |
| `IsActive` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `ValueSemantic` | `VARCHAR` | `YES` | `` |
| `Unit` | `VARCHAR` | `YES` | `` |

### main.dim_indicator_config (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `NO` | `nextval('CherryMon.main.seq_indicator_config')` |
| `ConfigCode` | `VARCHAR` | `NO` | `` |
| `IndicatorCode` | `VARCHAR` | `NO` | `` |
| `Timeframe` | `VARCHAR` | `NO` | `` |
| `Parameters` | `JSON` | `NO` | `` |
| `WarmupBars` | `INTEGER` | `YES` | `` |
| `IsEnabled` | `BOOLEAN` | `NO` | `CAST('t' AS BOOLEAN)` |
| `Description` | `VARCHAR` | `YES` | `` |
| `CreatedAt` | `TIMESTAMP` | `NO` | `CURRENT_TIMESTAMP` |
| `UpdatedAt` | `TIMESTAMP` | `YES` | `` |

### main.raw_active_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_bctc_cdkt (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `index` | `VARCHAR` | `YES` | `` |
| `column01` | `VARCHAR` | `YES` | `` |
| `Bất động sản đầu tư` | `BIGINT` | `YES` | `` |
| `Các khoản phải thu ngắn hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính dài hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính ngắn hạn` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Giai đoạn` | `VARCHAR` | `YES` | `` |
| `Hàng tồn kho` | `BIGINT` | `YES` | `` |
| `Hợp nhất` | `VARCHAR` | `YES` | `` |
| `Kiểm toán` | `VARCHAR` | `YES` | `` |
| `Lợi nhuận sau thuế chưa phân phối` | `BIGINT` | `YES` | `` |
| `Lợi ích của cổ đông thiểu số` | `BIGINT` | `YES` | `` |
| `Nợ dài hạn` | `BIGINT` | `YES` | `` |
| `Nợ ngắn hạn` | `BIGINT` | `YES` | `` |
| `Nợ phải trả` | `BIGINT` | `YES` | `` |
| `Thặng dư vốn cổ phần` | `BIGINT` | `YES` | `` |
| `Tiền và các khoản tương đương tiền` | `BIGINT` | `YES` | `` |
| `Tài sản cố định` | `BIGINT` | `YES` | `` |
| `Tài sản dài hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn khác` | `BIGINT` | `YES` | `` |
| `Tổng cộng nguồn vốn` | `BIGINT` | `YES` | `` |
| `Tổng cộng tài sản` | `BIGINT` | `YES` | `` |
| `Vốn chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Vốn đầu tư của chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |

### main.raw_bctc_cstc (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `index` | `VARCHAR` | `YES` | `` |
| `column01` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên giá trị sổ sách (P/B)` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên thu nhập (P/E)` | `VARCHAR` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Giai đoạn` | `VARCHAR` | `YES` | `` |
| `Giá trị sổ sách của cổ phiếu (BVPS)` | `VARCHAR` | `YES` | `` |
| `Hợp nhất` | `VARCHAR` | `YES` | `` |
| `Khả năng thanh toán lãi vay` | `VARCHAR` | `YES` | `` |
| `Kiểm toán` | `VARCHAR` | `YES` | `` |
| `Thu nhập trên mỗi cổ phần của 4 quý gần nhất (EPS)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận gộp biên` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận trên vốn chủ sở hữu bình quân (ROEA)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên doanh thu thuần` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên tổng tài sản bình quân (ROAA)` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ trên Tổng tài sản` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ vay trên Vốn chủ sở hữu` | `VARCHAR` | `YES` | `` |
| `Tỷ số thanh toán hiện hành (ngắn hạn)` | `VARCHAR` | `YES` | `` |
| `Ý kiến kiểm toán` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |

### main.raw_bctc_kqkd (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `index` | `VARCHAR` | `YES` | `` |
| `column01` | `VARCHAR` | `YES` | `` |
| `Chi phí bán hàng` | `BIGINT` | `YES` | `` |
| `Chi phí quản lý doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Chi phí tài chính` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Doanh thu hoạt động tài chính` | `BIGINT` | `YES` | `` |
| `Doanh thu thuần về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Giai đoạn` | `VARCHAR` | `YES` | `` |
| `Giá vốn hàng bán` | `BIGINT` | `YES` | `` |
| `Hợp nhất` | `VARCHAR` | `YES` | `` |
| `Kiểm toán` | `VARCHAR` | `YES` | `` |
| `Lãi cơ bản trên cổ phiếu (VNÐ)` | `BIGINT` | `YES` | `` |
| `Lợi nhuận gộp về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận khác` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế của cổ đông Công ty mẹ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế thu nhập doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Lợi nhuận thuần từ hoạt động kinh doanh` | `BIGINT` | `YES` | `` |
| `Phần lợi nhuận/lỗ từ công ty liên kết liên doanh` | `BIGINT` | `YES` | `` |
| `Tổng lợi nhuận kế toán trước thuế` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |

### main.raw_commodity_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_foreign_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_futures_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_futures_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_index_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_index_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_industry_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_lstTicker (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Stock` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Company Name` | `VARCHAR` | `YES` | `` |
| `Industry` | `VARCHAR` | `YES` | `` |
| `IndustryCode` | `VARCHAR` | `YES` | `` |
| `Expected Price` | `DOUBLE` | `YES` | `` |
| `Watchlist` | `VARCHAR` | `YES` | `` |
| `EcoSystem` | `DOUBLE` | `YES` | `` |
| `Sở hữu Nhà Nước` | `DOUBLE` | `YES` | `` |
| `Owner Type` | `VARCHAR` | `YES` | `` |
| `Margin` | `VARCHAR` | `YES` | `` |
| `Status` | `VARCHAR` | `YES` | `` |
| `Notes` | `DOUBLE` | `YES` | `` |

### main.raw_market_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_other_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_prop_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_stock_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_stock_fa (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `YES` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Full Name` | `VARCHAR` | `YES` | `` |
| `Market` | `VARCHAR` | `YES` | `` |
| `Capital` | `BIGINT` | `YES` | `` |
| `Sector` | `VARCHAR` | `YES` | `` |
| `ICB ID` | `BIGINT` | `YES` | `` |
| `ICB` | `VARCHAR` | `YES` | `` |
| `Industry` | `VARCHAR` | `YES` | `` |
| `Shares Float` | `BIGINT` | `YES` | `` |
| `Shares Outstanding` | `BIGINT` | `YES` | `` |
| `EPS` | `DOUBLE` | `YES` | `` |
| `PE` | `DOUBLE` | `YES` | `` |
| `Book Value` | `DOUBLE` | `YES` | `` |
| `ROA` | `DOUBLE` | `YES` | `` |
| `ROE` | `DOUBLE` | `YES` | `` |

### main.raw_stock_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_supplydemand_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_tblBCTC (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `DT` | `DATE` | `YES` | `` |
| `Quarter` | `VARCHAR` | `YES` | `` |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Chi phí bán hàng` | `BIGINT` | `YES` | `` |
| `Chi phí quản lý doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Chi phí tài chính` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán` | `VARCHAR` | `YES` | `` |
| `Doanh thu hoạt động tài chính` | `BIGINT` | `YES` | `` |
| `Doanh thu thuần về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Giai đoạn (kqkd)` | `VARCHAR` | `YES` | `` |
| `Giá vốn hàng bán` | `BIGINT` | `YES` | `` |
| `Hợp nhất (kqkd)` | `VARCHAR` | `YES` | `` |
| `Kiểm toán (kqkd)` | `VARCHAR` | `YES` | `` |
| `Lãi cơ bản trên cổ phiếu (VNÐ)` | `BIGINT` | `YES` | `` |
| `Lợi nhuận gộp về bán hàng và cung cấp dịch vụ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận khác` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế của cổ đông Công ty mẹ` | `BIGINT` | `YES` | `` |
| `Lợi nhuận sau thuế thu nhập doanh nghiệp` | `BIGINT` | `YES` | `` |
| `Lợi nhuận thuần từ hoạt động kinh doanh` | `BIGINT` | `YES` | `` |
| `Phần lợi nhuận/lỗ từ công ty liên kết liên doanh` | `BIGINT` | `YES` | `` |
| `Tổng lợi nhuận kế toán trước thuế` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán (kqkd)` | `VARCHAR` | `YES` | `` |
| `Bất động sản đầu tư` | `BIGINT` | `YES` | `` |
| `Các khoản phải thu ngắn hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính dài hạn` | `BIGINT` | `YES` | `` |
| `Các khoản đầu tư tài chính ngắn hạn` | `BIGINT` | `YES` | `` |
| `Công ty kiểm toán (cdkt)` | `VARCHAR` | `YES` | `` |
| `Giai đoạn (cdkt)` | `VARCHAR` | `YES` | `` |
| `Hàng tồn kho` | `BIGINT` | `YES` | `` |
| `Hợp nhất (cdkt)` | `VARCHAR` | `YES` | `` |
| `Kiểm toán (cdkt)` | `VARCHAR` | `YES` | `` |
| `Lợi nhuận sau thuế chưa phân phối` | `BIGINT` | `YES` | `` |
| `Lợi ích của cổ đông thiểu số` | `BIGINT` | `YES` | `` |
| `Nợ dài hạn` | `BIGINT` | `YES` | `` |
| `Nợ ngắn hạn` | `BIGINT` | `YES` | `` |
| `Nợ phải trả` | `BIGINT` | `YES` | `` |
| `Thặng dư vốn cổ phần` | `BIGINT` | `YES` | `` |
| `Tiền và các khoản tương đương tiền` | `BIGINT` | `YES` | `` |
| `Tài sản cố định` | `BIGINT` | `YES` | `` |
| `Tài sản dài hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn` | `BIGINT` | `YES` | `` |
| `Tài sản ngắn hạn khác` | `BIGINT` | `YES` | `` |
| `Tổng cộng nguồn vốn` | `BIGINT` | `YES` | `` |
| `Tổng cộng tài sản` | `BIGINT` | `YES` | `` |
| `Vốn chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Vốn đầu tư của chủ sở hữu` | `BIGINT` | `YES` | `` |
| `Ý kiến kiểm toán (cdkt)` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên giá trị sổ sách (P/B)` | `VARCHAR` | `YES` | `` |
| `Chỉ số giá thị trường trên thu nhập (P/E)` | `VARCHAR` | `YES` | `` |
| `Công ty kiểm toán (cstc)` | `VARCHAR` | `YES` | `` |
| `Giai đoạn (cstc)` | `VARCHAR` | `YES` | `` |
| `Giá trị sổ sách của cổ phiếu (BVPS)` | `VARCHAR` | `YES` | `` |
| `Hợp nhất (cstc)` | `VARCHAR` | `YES` | `` |
| `Khả năng thanh toán lãi vay (TIE)` | `VARCHAR` | `YES` | `` |
| `Kiểm toán (cstc)` | `VARCHAR` | `YES` | `` |
| `Thu nhập trên mỗi cổ phần của 4 quý gần nhất (EPS)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận gộp biên (GPM)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất lợi nhuận trên vốn chủ sở hữu bình quân (ROEA)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên doanh thu thuần (ROS)` | `VARCHAR` | `YES` | `` |
| `Tỷ suất sinh lợi trên tổng tài sản bình quân (ROAA)` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ trên Tổng tài sản (DAR)` | `VARCHAR` | `YES` | `` |
| `Tỷ số Nợ vay trên Vốn chủ sở hữu (D/E)` | `VARCHAR` | `YES` | `` |
| `Tỷ số thanh toán hiện hành (Current Ratio)` | `VARCHAR` | `YES` | `` |
| `Ý kiến kiểm toán (cstc)` | `VARCHAR` | `YES` | `` |

### main.raw_warrant_eod (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.raw_warrant_intraday (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `NO` | `` |
| `Date` | `DATE` | `NO` | `` |
| `Open` | `DOUBLE` | `YES` | `` |
| `High` | `DOUBLE` | `YES` | `` |
| `Low` | `DOUBLE` | `YES` | `` |
| `Close` | `DOUBLE` | `YES` | `` |
| `Volume` | `BIGINT` | `YES` | `` |
| `OpenInt` | `DOUBLE` | `YES` | `` |

### main.sys_data_quality_audit (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `validation_id` | `VARCHAR` | `YES` | `` |
| `checked_at` | `TIMESTAMP` | `YES` | `` |
| `pipeline_name` | `VARCHAR` | `YES` | `` |
| `table_name` | `VARCHAR` | `YES` | `` |
| `expected_date` | `DATE` | `YES` | `` |
| `max_date` | `DATE` | `YES` | `` |
| `status` | `VARCHAR` | `YES` | `` |
| `row_count_current` | `BIGINT` | `YES` | `` |
| `row_count_previous` | `BIGINT` | `YES` | `` |
| `row_count_change_pct` | `DOUBLE` | `YES` | `` |
| `symbol_count_current` | `BIGINT` | `YES` | `` |
| `symbol_count_previous` | `BIGINT` | `YES` | `` |
| `symbol_count_change_pct` | `DOUBLE` | `YES` | `` |
| `missing_symbol_count` | `BIGINT` | `YES` | `` |
| `new_symbol_count` | `BIGINT` | `YES` | `` |
| `duplicate_count` | `BIGINT` | `YES` | `` |
| `row_count_zscore` | `DOUBLE` | `YES` | `` |
| `symbol_count_zscore` | `DOUBLE` | `YES` | `` |
| `metrics` | `JSON` | `YES` | `` |
| `errors` | `JSON` | `YES` | `` |
| `warnings` | `JSON` | `YES` | `` |

### main.t (BASE TABLE)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `NO` | `` |
| `value` | `VARCHAR` | `YES` | `` |

### main.vw_ACCCNNTD (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `NetVol` | `DOUBLE` | `YES` | `` |
| `NetVal` | `DOUBLE` | `YES` | `` |
| `BuyVol` | `DOUBLE` | `YES` | `` |
| `BuyVal` | `DOUBLE` | `YES` | `` |
| `SellVol` | `DOUBLE` | `YES` | `` |
| `SellVal` | `BIGINT` | `YES` | `` |
| `DataSource` | `VARCHAR` | `YES` | `` |

### main.vw_ACCCNNTD_Price (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `AvgPrice` | `DOUBLE` | `YES` | `` |
| `AC_NetVol` | `DOUBLE` | `YES` | `` |
| `NN_NetVol` | `DOUBLE` | `YES` | `` |
| `TD_NetVol` | `DOUBLE` | `YES` | `` |
| `CC_NetVol` | `DOUBLE` | `YES` | `` |
| `AC_NetVal` | `DOUBLE` | `YES` | `` |
| `NN_NetVal` | `DOUBLE` | `YES` | `` |
| `TD_NetVal` | `DOUBLE` | `YES` | `` |
| `CC_NetVal` | `DOUBLE` | `YES` | `` |

### main.vw_Indicator_config (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ConfigCode` | `VARCHAR` | `YES` | `` |
| `IndicatorCode` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `Parameters` | `JSON` | `YES` | `` |
| `WarmupBars` | `INTEGER` | `YES` | `` |
| `ConfigIsEnabled` | `BOOLEAN` | `YES` | `` |
| `ConfigDescription` | `VARCHAR` | `YES` | `` |
| `ConfigCreatedAt` | `TIMESTAMP` | `YES` | `` |
| `ConfigUpdatedAt` | `TIMESTAMP` | `YES` | `` |
| `IndicatorName` | `VARCHAR` | `YES` | `` |
| `Category` | `VARCHAR` | `YES` | `` |
| `Engine` | `VARCHAR` | `YES` | `` |
| `FunctionName` | `VARCHAR` | `YES` | `` |
| `RequiredInputs` | `JSON` | `YES` | `` |
| `ParameterSchema` | `JSON` | `YES` | `` |
| `IndicatorDescription` | `VARCHAR` | `YES` | `` |
| `IndicatorIsActive` | `BOOLEAN` | `YES` | `` |
| `IndicatorCreatedAt` | `TIMESTAMP` | `YES` | `` |
| `IndicatorUpdatedAt` | `TIMESTAMP` | `YES` | `` |
| `ComponentCode` | `VARCHAR` | `YES` | `` |
| `ComponentName` | `VARCHAR` | `YES` | `` |
| `OutputPrefix` | `VARCHAR` | `YES` | `` |
| `SortOrder` | `INTEGER` | `YES` | `` |
| `ValueSemantic` | `VARCHAR` | `YES` | `` |
| `Unit` | `VARCHAR` | `YES` | `` |
| `IsPrimary` | `BOOLEAN` | `YES` | `` |
| `ComponentIsActive` | `BOOLEAN` | `YES` | `` |

### main.vw_Ticker (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Stock` | `VARCHAR` | `YES` | `` |
| `Company Name` | `VARCHAR` | `YES` | `` |
| `Industry` | `VARCHAR` | `YES` | `` |
| `IndustryCode` | `VARCHAR` | `YES` | `` |
| `Status` | `VARCHAR` | `YES` | `` |
| `Capital` | `BIGINT` | `YES` | `` |
| `Shares Outstanding` | `BIGINT` | `YES` | `` |
| `EPS` | `DOUBLE` | `YES` | `` |
| `PE` | `DOUBLE` | `YES` | `` |
| `Book Value` | `DOUBLE` | `YES` | `` |
| `ROA` | `DOUBLE` | `YES` | `` |
| `ROE` | `DOUBLE` | `YES` | `` |

### main.vw_Ticker_indicators (VIEW)

| Column | Type | Nullable | Default |
| --- | --- | --- | --- |
| `Ticker` | `VARCHAR` | `YES` | `` |
| `Date` | `DATE` | `YES` | `` |
| `ConfigId` | `BIGINT` | `YES` | `` |
| `ComponentCode` | `VARCHAR` | `YES` | `` |
| `Value` | `DOUBLE` | `YES` | `` |
| `IndicatorCode` | `VARCHAR` | `YES` | `` |
| `Timeframe` | `VARCHAR` | `YES` | `` |
| `WarmupBars` | `INTEGER` | `YES` | `` |

## Indicator metadata snapshots

| DuckDB source | CSV file | Rows |
| --- | --- | ---: |
| `CherryMon`.`main`.`dim_indicator` | `dim_indicator.csv` | 66 |
| `CherryMon`.`main`.`dim_indicator_component` | `dim_indicator_component.csv` | 8 |
| `CherryMon`.`main`.`dim_indicator_config` | `dim_indicator_config.csv` | 21 |
