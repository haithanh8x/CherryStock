UPDATE "CherryMon"."main"."dimCalendar"
SET isHoliday = CASE 
    WHEN DayNameOfWeek IN ('Saturday', 'Sunday') THEN 'Y'
    WHEN EXISTS (
        SELECT 1 
        FROM "CherryMon"."main"."raw_index_eod"
        WHERE "raw_index_eod".Date = "dimCalendar".FullDate
          AND "raw_index_eod".Ticker = 'VNINDEX'
    ) THEN 'N'
    ELSE 'Y'
END;
