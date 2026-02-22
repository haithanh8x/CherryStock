set home_directory="C:\Users\ADMIN\OneDrive - ollyo\Datafile\";
CREATE OR REPLACE TABLE tblBCTC AS
WITH ab AS (
    SELECT
        COALESCE(a."index", b."index") AS "index",
        COALESCE(a."Ticker", b."Ticker") AS "Ticker",
        -- Table A
        a."Doanh thu thuần",
        a."LN thuần từ HĐKD",
        a."LNST của CĐ cty mẹ",
        a."LNST thu nhập DN",
        a."Lợi nhuận gộp",
        -- Table B
        b."Lợi ích của CĐ thiểu số",
        b."Nợ ngắn hạn",
        b."Nợ phải trả",
        b."Tài sản ngắn hạn",
        b."Tổng tài sản",
        b."Vốn chủ sở hữu"
    FROM read_csv_auto(current_setting('home_directory')||'BCTQ_table0_MWG.csv') a
    FULL OUTER JOIN read_csv_auto(current_setting('home_directory')||'BCTQ_table1_MWG.csv') b
        ON a."Ticker" = b."Ticker"
        AND a."index" = b."index"
)
SELECT
    COALESCE(ab."index", c."index") AS "Quarter",
    COALESCE(ab."Ticker", c."Ticker") AS "Ticker",
    -- Table A fields
    ab."Doanh thu thuần",
    ab."LN thuần từ HĐKD",
    ab."LNST của CĐ cty mẹ",
    ab."LNST thu nhập DN",
    ab."Lợi nhuận gộp",
    -- Table B fields
    ab."Lợi ích của CĐ thiểu số",
    ab."Nợ ngắn hạn",
    ab."Nợ phải trả",
    ab."Tài sản ngắn hạn",
    ab."Tổng tài sản",
    ab."Vốn chủ sở hữu",
    -- Table C fields
    c."BVPS cơ bản",
    c."EPS 4 quý",
    c."P/E cơ bản",
    c."ROAA",
    c."ROEA",
    c."ROS"

FROM ab
FULL OUTER JOIN read_csv_auto(current_setting('home_directory')||'BCTQ_table2_MWG.csv') c
    ON ab."Ticker" = c."Ticker"
    AND ab."index" = c."index";