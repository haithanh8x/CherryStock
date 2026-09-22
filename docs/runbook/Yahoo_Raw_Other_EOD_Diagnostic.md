# Runbook — Yahoo raw_other_eod invalid OHLC Diagnostic

- **Purpose:** Diagnose the core daily Yahoo Finance DQ blocker
  `raw_other_eod invalid_ohlc_count > 0`.
- **Scope:** Read-only diagnosis by default.
- **Table:** `"CherryMon"."main"."raw_other_eod"`
- **Pipeline:** `Yahoo Finance EOD`
- **Yahoo scope:** `DX-Y.NYB`, `BTC-USD`, `VND=X`, `GC=F`
- **Script:** `scripts/diagnose_yahoo_raw_other_eod.py`

## 1. Exact DQ Rule Being Reproduced

The production generic DataValidation rule marks a row invalid when any condition is true:

```text
High < Low
High < Open
High < Close
Low  > Open
Low  > Close
```

The production Yahoo EOD DQ applies this rule to the latest date in the configured
`YAHOO_OTHER_TICKERS` scope.

The diagnostic does **not** modify this rule.

## 2. What the Diagnostic Adds

For each row on the target date it reports:

```text
HighLtLow
HighLtOpen
HighLtClose
LowGtOpen
LowGtClose
RuleFlags
MaxViolationAbs
MaxViolationBps
DiagnosticClass
```

DiagnosticClass is explanatory only:

```text
CLEAN
FLOAT_PRECISION_CANDIDATE
MATERIAL_OHLC_ENVELOPE_VIOLATION
```

The default precision-label threshold is `0.01 bps`.

This threshold does **not** alter DataValidation and does not make an invalid row valid.

The script also returns neighboring DB rows for the offending ticker and the most recent persisted
Yahoo DQ audit rows when available.

## 3. Important Audit Caveat

The normal core daily pipeline performs Yahoo validation inside the shared DuckDB UnitOfWork.

If Yahoo DQ raises and the core UoW rolls back, a FAIL audit row written in the same transaction may
also roll back.

Therefore:

```text
sys_data_quality_audit
= supporting evidence only

raw_other_eod + exact DQ reproduction
= primary diagnostic evidence
```

The diagnostic must continue to work even if no recent FAIL audit row exists.

## 4. Phase 0 — Sync Branch

```powershell
cd C:\Github\CherryStock
git status --short
git fetch origin
git switch feature/yahoo-raw-other-eod-diagnostic
git pull origin feature/yahoo-raw-other-eod-diagnostic
```

Preserve unrelated local changes.

## 5. Phase 1 — Compile + Focused Tests

```powershell
python -m compileall src\cherrystock\application\services\yahoo_eod_diagnostic.py scripts\diagnose_yahoo_raw_other_eod.py

python -m pytest tests\test_yahoo_eod_diagnostic.py tests\test_data_validation.py tests\test_data_quality_orchestration.py -v
```

Expected: PASS.

## 6. Phase 2 — DB-only Diagnostic

Run without network refetch first:

```powershell
$evidence = "docs\reference\data\data_quality\yahoo_raw_other_eod"

python scripts\diagnose_yahoo_raw_other_eod.py --evidence-dir $evidence --allow-invalid
```

Expected for the currently known blocker:

```text
invalid_ohlc_count: 1
```

Review:

```text
Ticker
Date
Open
High
Low
Close
RuleFlags
MaxViolationAbs
MaxViolationBps
DiagnosticClass
```

Generated evidence:

```text
Yahoo_Raw_Other_EOD_Diagnostic_Summary.json
Yahoo_Raw_Other_EOD_Target_Date.csv
Yahoo_Raw_Other_EOD_Invalid_Rows.csv
Yahoo_Raw_Other_EOD_Context.csv
Yahoo_Raw_Other_EOD_Audit.csv
```

Without `--allow-invalid`, the script exits code `2` when invalid OHLC exists. This is intentional.

## 7. Phase 3 — Refetch Only the Offending Yahoo Row

After identifying the invalid ticker/date, compare the stored row with Yahoo's current adjusted EOD:

```powershell
python scripts\diagnose_yahoo_raw_other_eod.py --refetch-yahoo --evidence-dir $evidence --allow-invalid
```

The refetch uses the same important source semantics as ingestion:

```text
interval = 1d
auto_adjust = True
end date = exclusive
```

Additional evidence:

```text
Yahoo_Raw_Other_EOD_Provider_Compare.csv
```

ProviderComparison values:

### SOURCE_YAHOO_CANDIDATE

```text
DB row invalid
+
fresh Yahoo row also violates OHLC envelope
```

Interpretation: upstream adjusted Yahoo data itself is a strong root-cause candidate.

Do not silently repair High/Low in CherryMon.

### DB_DIFFERS_PROVIDER

```text
DB row invalid
+
fresh Yahoo row is materially different
```

Interpretation: source history may have changed, or the stored row may be stale.

Preferred next diagnostic is exact-date resync, then rerun this script.

### PROVIDER_NOW_VALID_DB_NEAR_MATCH

Yahoo currently returns a valid row and values are very close to the stored row.

If the DB violation is tiny, this strengthens a floating-point/adjusted-price precision hypothesis.

### PROVIDER_UNAVAILABLE

No exact target-date provider row was returned. Do not infer the source is clean or invalid.

## 8. Phase 4 — Direct SQL Cross-check

The exact production OHLC predicate can also be inspected directly:

```sql
WITH scope AS (
    SELECT *
    FROM "CherryMon"."main"."raw_other_eod"
    WHERE Ticker IN ('DX-Y.NYB', 'BTC-USD', 'VND=X', 'GC=F')
),
latest AS (
    SELECT MAX(Date) AS Date
    FROM scope
)
SELECT
    s.Ticker,
    s.Date,
    s.Open,
    s.High,
    s.Low,
    s.Close,
    s.Volume,
    s.High < s.Low   AS HighLtLow,
    s.High < s.Open  AS HighLtOpen,
    s.High < s.Close AS HighLtClose,
    s.Low  > s.Open  AS LowGtOpen,
    s.Low  > s.Close AS LowGtClose
FROM scope s
JOIN latest l USING (Date)
WHERE s.High < s.Low
   OR s.High < s.Open
   OR s.High < s.Close
   OR s.Low > s.Open
   OR s.Low > s.Close
ORDER BY s.Ticker;
```

Expected result count should equal the diagnostic `invalid_ohlc_count`.

## 9. Phase 5 — Optional Exact-date Resync Test

Only use this phase if ProviderComparison indicates the current Yahoo row differs from the DB.

Do not manually UPDATE High/Low/Open/Close.

Use the existing canonical Yahoo sync path for the offending date range. Because yfinance `end`
is exclusive, the end date must be target date + 1 calendar day.

Example pattern:

```powershell
python -c "from src.CrawlStock.readYahooFinance import syncYahooFinance_EOD; from src.cherrystock.config.settings import settings; from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory; from datetime import date,timedelta; f=DuckDBConnectionFactory(db_path=settings.local_db_path); d=date.fromisoformat('<YYYY-MM-DD>'); c=f.writer(); syncYahooFinance_EOD(connection=c,start_date=d.isoformat(),end_date=(d+timedelta(days=1)).isoformat()); c.commit(); c.close()"
```

Before executing this on the production local DB, verify there are no unrelated uncommitted database
operations and keep a backup if required by your local operating procedure.

Then rerun:

```powershell
python scripts\diagnose_yahoo_raw_other_eod.py --refetch-yahoo --allow-invalid
```

If the invalid count becomes zero, rerun the standard core pipeline later through `run.py`.

## 10. Root-cause Decision Table

| DB result | Fresh Yahoo result | Likely candidate | Next step |
|---|---|---|---|
| Material invalid | Material invalid | Yahoo adjusted-source anomaly | Capture evidence; define source-specific DQ policy separately |
| Material invalid | Valid and materially different | Stored row stale/source history changed | Exact-date canonical resync, then revalidate |
| Tiny invalid | Same/tiny provider violation | Floating-point precision candidate | Capture exact deltas; evaluate tolerance in separate change |
| Invalid | No provider row | Inconclusive | Retry provider later / inspect Yahoo directly |
| Clean | Clean | Blocker no longer reproducible | Run normal DQ / run.py |

## 11. Do Not Do During Diagnosis

Do not:

- clamp `High = max(Open, High, Close)`;
- clamp `Low = min(Open, Low, Close)`;
- round all Yahoo prices globally;
- add a tolerance to production DataValidation;
- exclude the ticker from `YAHOO_OTHER_TICKERS`;
- bypass `raise_on_fail=True`.

Any production policy change requires evidence from this diagnostic first.

## 12. Evidence Commit

If diagnosis identifies the concrete offending ticker/date and provider comparison:

```powershell
git add docs\reference\data\data_quality\yahoo_raw_other_eod
git commit -m "diagnostic: capture Yahoo raw_other_eod OHLC failure evidence"
git push origin feature/yahoo-raw-other-eod-diagnostic
```

Do not commit database files or unrelated workspace changes.

## 13. Diagnostic Verdict Template

```text
YAHOO RAW_OTHER_EOD DIAGNOSTIC

Target date:
<YYYY-MM-DD>

Invalid OHLC count:
<N>

Offending ticker:
<TICKER>

Rule flags:
<HIGH_LT_CLOSE | ...>

Stored OHLC:
O=<...> H=<...> L=<...> C=<...>

Max violation:
<abs>
<bps>

Diagnostic class:
FLOAT_PRECISION_CANDIDATE | MATERIAL_OHLC_ENVELOPE_VIOLATION

Fresh Yahoo comparison:
SOURCE_YAHOO_CANDIDATE | DB_DIFFERS_PROVIDER |
PROVIDER_NOW_VALID_DB_NEAR_MATCH | PROVIDER_UNAVAILABLE

Recommended next action:
<evidence-based action>
```
