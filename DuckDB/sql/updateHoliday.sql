UPDATE "CherryMon"."main"."dimCalendar"
SET isHoliday = 'Y'
WHERE DayNameOfWeek NOT IN ('Sarturday', 'Sunday')
  AND NOT EXISTS (
    SELECT 1 
    FROM "CherryMon"."main"."raw_index_eod"
    WHERE "raw_index_eod".Date = "dimCalendar".FullDate
      AND "raw_index_eod".Ticker = 'VNINDEX'
  )