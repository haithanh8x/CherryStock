# Yahoo Finance EOD Historical Backfill

- **Status:** ACTIVE
- **Objective:** restore and preserve Yahoo Finance EOD history from `2024-04-01` in `"CherryMon"."main"."raw_other_eod"`.
- **Initload script:** `scripts/initload/initload_yahoo_eod.py`
- **Production adapter:** `src/CrawlStock/readYahooFinance.py`
- **Logical key:** `Ticker + Date`

## 1. Root cause

Yahoo daily ingestion itself is already idempotent:

```sql
INSERT ...
ON CONFLICT (Ticker, Date) DO UPDATE
```

Normal daily execution calls:

```text
syncYahooFinance_EOD(from_last_day=days_diff)
```

and only requests a recent Yahoo window. It does **not** delete historical Yahoo rows.

The historical-loss risk comes from the shared target:

```text
AmiBroker EOD/other ─┐
                     ├─> raw_other_eod
Yahoo Finance EOD ───┘
```

AmiBroker full EOD mode uses `from_last_day=None` and rebuilds its configured target tables. Because `raw_other_eod` is one of those targets, a full AmiBroker reload can remove previously stored Yahoo history. A later daily Yahoo checkpoint then only upserts the recent window, which explains why the table can contain only several recent Yahoo rows.

Canonical full-load scripts now restore Yahoo history automatically after AmiBroker EOD rebuild:

```text
scripts/initload/init_reload_raw_eod_tables.py
scripts/initload/init_reload_raw_eod_raw_intraday.py
```

Both call:

```text
syncYahooFinance_EOD(start_date="2024-04-01")
```

after the destructive AmiBroker EOD phase.

---

## 2. One-time historical initload

Run from repository root:

```powershell
git pull
python scripts\initload\initload_yahoo_eod.py
```

Default scope:

```text
start = 2024-04-01 inclusive
end   = latest Yahoo data available
```

Configured tickers:

```text
DX-Y.NYB
BTC-USD
VND=X
GC=F
```

The script uses production `syncYahooFinance_EOD()` and persists with:

```text
ON CONFLICT (Ticker, Date) DO UPDATE
```

It does not truncate or delete the existing table.

---

## 3. Optional bounded backfill

Yahoo `end` is exclusive.

Example:

```powershell
python scripts\initload\initload_yahoo_eod.py --start 2024-04-01 --end 2025-01-01
```

This requests:

```text
2024-04-01 <= Date < 2025-01-01
```

For the required full history, omit `--end`.

---

## 4. Expected validation

At completion the script prints one row per configured Yahoo ticker:

```text
Ticker      min_date      max_date      row_count
...
Duplicate Ticker+Date groups: 0
PASS: historical Yahoo EOD window is present and logical keys are unique.

=== Verdict ===
PASS
Action: KEEP + STOP
```

Because Yahoo instruments use mixed calendars, the first row is allowed to occur within seven calendar days after the requested start date. The validation does not require all four symbols to share identical dates.

---

## 5. SQL cross-check

```sql
SELECT
    Ticker,
    MIN(Date) AS MinDate,
    MAX(Date) AS MaxDate,
    COUNT(*) AS Rows
FROM "CherryMon"."main"."raw_other_eod"
WHERE Ticker IN ('DX-Y.NYB', 'BTC-USD', 'VND=X', 'GC=F')
GROUP BY Ticker
ORDER BY Ticker;
```

Expected after backfill:

```text
MinDate should be at or near 2024-04-01 for every configured Yahoo ticker.
MaxDate should match the latest available Yahoo date for that instrument/calendar.
```

Duplicate check:

```sql
SELECT Ticker, Date, COUNT(*) AS Rows
FROM "CherryMon"."main"."raw_other_eod"
WHERE Ticker IN ('DX-Y.NYB', 'BTC-USD', 'VND=X', 'GC=F')
GROUP BY Ticker, Date
HAVING COUNT(*) > 1;
```

Expected:

```text
0 rows
```

---

## 6. Idempotency test

After the first successful initload, run the exact same command once more:

```powershell
python scripts\initload\initload_yahoo_eod.py
```

PASS criteria:

```text
no duplicate Ticker+Date
same historical coverage
existing rows updated in place when Yahoo values differ
no historical rows removed
Verdict: PASS
```

Do not run a third time merely for confidence.

---

## 7. Daily behavior after initload

Normal execution remains unchanged:

```powershell
python run.py
```

Daily flow:

```text
recent checkpoint window
    ↓
Yahoo download
    ↓
normalize
    ↓
INSERT ... ON CONFLICT DO UPDATE
    ↓
Yahoo Data Quality
```

The daily checkpoint should only add/update recent dates. It must not delete history from `2024-04-01` onward.

---

## 8. Full AmiBroker reload behavior after fix

These commands are allowed:

```powershell
python scripts\initload\init_reload_raw_eod_tables.py
python scripts\initload\init_reload_raw_eod_raw_intraday.py
```

Their EOD phase still follows the existing AmiBroker full-rebuild contract. However, because `raw_other_eod` is shared, the scripts now immediately execute Yahoo historical upsert from `2024-04-01` before completion.

Expected final state:

```text
AmiBroker EOD/other rows
+
Yahoo historical rows from 2024-04-01
```

Do not remove the Yahoo-restore stage from these full-load scripts while both sources continue sharing `raw_other_eod`.

---

## 9. Focused test commands

Run from repository root:

```powershell
python -m pytest tests\test_read_yahoo_finance.py --collect-only -q
python -m pytest tests\test_read_yahoo_finance.py -v
```

Then execute the real-data initload once:

```powershell
python scripts\initload\initload_yahoo_eod.py
```

If unit tests PASS and historical initload reports PASS, keep the change and STOP.

If the production Yahoo request fails, capture the exact ticker/error and STOP. Do not delete existing `raw_other_eod` rows and do not rerun unchanged commands repeatedly.

---

## 10. Terminal result format

```text
Target: Yahoo EOD historical coverage from 2024-04-01
Unit test: PASS / FAIL / BLOCKED
Historical initload: PASS / FAIL / BLOCKED
Duplicate Ticker+Date: 0 / non-zero
Min/Max date per ticker: <paste output>
Action: KEEP / FIX ONCE / STOP
```
