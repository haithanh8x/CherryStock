# SmartMoney popup fixes & ticker timing — local deployment runbook

Status: IMPLEMENTED_PENDING_VALIDATION
Implementation commit: f224b8ac6ae99476abb36639cdb41986677ac362
Deployment branch: feature/smartmoney-popup-fixes-timing
Runbook location: main
Entry: src/webapp/NiceGUI_chart.py → SmartMoney
Next owner: local TestEngineer

## 1. Accepted backlog and scope

1. Replace the extra sandboxed srcdoc TradingView wrapper with the official
   external-embedding loader mounted into a live 620px DOM container. Preserve
   qualified Vietnamese symbol, attribution, locked symbol and direct link.
2. Use R/S-style tooltip background, border, padding, type and layout:
   bold title, wrapped explanation, separate illustrative example; hover/focus.
3. All ticker links bold; BUY positive, HOLD warning, SELL negative, unknown muted.
   Hover/active/focus use the same action color.
4. Remove MA200 column headings and segmentation from the displayed state list.
5. Remove commas between ticker links. Keep all rows, confidence order and anchors.
6. Measure read connections, each public view, market lookup, R/S, server rendering
   and TradingView lifecycle; export evidence for a later tuning decision.

No migration, initload, daily pipeline, full-universe test, cache or query tuning.
The state builder's MA200 diagnostics remain available; the UI shows block.rows.
R/S engine and three public view definitions/calculations are unchanged.
The opaque-origin sandbox is a suspected integration failure point, not a locally
confirmed production root cause. Real candles must be verified below.

## 2. Read / allowed repair scope

Read repository governance, GeneralCoding/TestEngineer agents, Python/testing
instructions, regression-testing skill and Python_Execution_Conventions.md.
Allowed files: src/webapp/{smart_money_tab,ticker_detail_dialog,ticker_detail_data,
ticker_detail_trace,tradingview_widget}.py; src/Presentation/theme.py;
scripts/profile_ticker_detail.py; corresponding focused tests;
docs/architecture/{Chart_Architecture,theme}.md; this runbook.
Do not alter engines, DB schema, calculations or unrelated pages.
Two focused repair attempts maximum; never rerun an unchanged failure.

## 3. Sync safely

Use the existing working NiceGUI Python environment, from repository root.
Stop only the current NiceGUI process.

~~~powershell
git status --short
$previousBranch = git branch --show-current
$previousCommit = git rev-parse HEAD
git fetch origin
~~~

If tree is dirty: preserve changes, BLOCKED/STOP; no automatic stash/reset.
Before this feature PR merges, deploy its branch (the runbook itself is on main):

~~~powershell
git switch --track origin/feature/smartmoney-popup-fixes-timing
~~~

If the local branch already exists:

~~~powershell
git switch feature/smartmoney-popup-fixes-timing
git pull --ff-only origin feature/smartmoney-popup-fixes-timing
~~~

After this feature PR merges, use:

~~~powershell
git switch main
git pull --ff-only origin main
~~~

Confirm git rev-parse HEAD includes implementation f224b8ac6ae99476abb36639cdb41986677ac362.
Do not test an older main and report a verdict for this fix.
For reference, the original popup PR #23 merged as 01093ac.

## 4. Compile and focused developer regression

~~~powershell
python -m py_compile src\webapp\smart_money_tab.py src\webapp\ticker_detail_dialog.py src\webapp\ticker_detail_data.py src\webapp\ticker_detail_trace.py src\webapp\tradingview_widget.py src\Presentation\theme.py scripts\profile_ticker_detail.py
python -m pytest tests\test_ticker_detail_contract.py tests\test_ticker_detail_dialog.py tests\test_ticker_detail_trace.py tests\test_ticker_detail_data_timing.py tests\test_smart_money_ticker_presentation.py tests\test_profile_ticker_detail.py tests\test_tradingview_links.py tests\test_smart_money_snapshot_query.py tests\test_smart_money_state_flow.py -q
~~~

Expected: 33 cases, exit 0. Collection failure is an import/environment blocker,
not a product regression. Use existing web dependencies, do not upgrade the project.

Developer evidence: 33 tests ran with in-memory module collection, actual NiceGUI
components and DuckDB fixtures; production DB/engine boundaries stubbed.
Python source compilation and node --check for mount JavaScript succeeded.
Headless browser smoke was BLOCKED: installed Playwright lacked Chromium.
No real TradingView candles or production latency measured in that environment.

## 5. Backend timing — baseline, then call hotspots

Run once with 3 tickers × 3 samples. Do not run the full universe.

~~~powershell
python scripts\profile_ticker_detail.py --tickers MWG SHS ACV --repeat 3
$baselineExit = $LASTEXITCODE
python scripts\profile_ticker_detail.py --tickers MWG --repeat 1 --profile
$profileExit = $LASTEXITCODE
~~~

If the baseline fails, inspect its bounded evidence and stop before profiling;
do not proceed through a broken import or DB connection. A nonzero code can mean
a partial source error; CSV is still exported after handled runtime errors.

Output under docs/reference/data/smart_money/ticker_detail_popup/:
- stages_baseline.csv: per request/sample/stage, status, duration and elapsed_ms.
- summary_baseline.csv: first sample, median, nearest-rank p95, max, error count.
- stages_profiled.csv / summary_profiled.csv: separate instrumented measurements.
- python_hotspots.csv: top 100 cumulative call sites per profiled sample,
  call counts, self_ms, cumulative_ms; filenames redacted to repo-relative/basename.

Same-mode reruns overwrite those CSVs; preserve the first evidence before rerunning.
First sample is merely first in process, not guaranteed cold DB/OS cache.
With only 3 samples p95 equals the maximum; it is not a production SLA estimate.
cProfile changes latency: use baseline for timing, profiled data only to locate
expensive calls, especially R/S source loaders and DuckDB execute.
No raw data records, SQL text, credentials or full database are exported.

## 6. Popup/browser timing and visual smoke (maximum 15 minutes)

~~~powershell
$env:CHERRYSTOCK_TICKER_TRACE = "1"
python src\webapp\NiceGUI_chart.py
~~~

Open http://127.0.0.1:8081 → SmartMoney in normal Chrome/Edge.

1. In each state: one wrapping list, all ticker links bold; no >= MA200,
   < MA200, MA200 N/A headings or comma separators. Total coverage and
   confidence order must match the snapshot; anchors and Refresh still work.
2. Check BUY/HOLD/SELL against row data: green/amber/red theme tokens respectively.
   Hover shows same-color tint and underline, keyboard focus clear; no layout shift.
   Unknown action uses muted; action name is available in the hint.
3. Open MWG, wait at most 20 seconds after the widget starts. Observe actual candles
   and HOSE:MWG (not merely an iframe event). Check R/S and all three local panels.
   Repeat SHS/HNX and ACV/UPCOM once each. If vendor says unsupported/no data,
   record the exact displayed reason; do not claim candle-render PASS for that symbol.
4. Close and reopen MWG three times, one at a time. Record observed click-to-content
   and click-to-candles duration; this includes browser transport/paint, unlike CLI.
5. Hover/focus one ticker, one field name/value and one R/S marker:
   same tooltip background/border/padding/text scale, title/explanation/example
   hierarchy, wrapping within viewport. Blur hides; Escape closes tooltip/popup.
6. Rapidly open another ticker / close during loading: no stale overwrite, no old
   widget remains. Ctrl/Cmd-click opens qualified external TradingView directly.
7. Block only the s3.tradingview.com loader in browser DevTools for one attempt:
   visible failure/fallback link, analytics still usable. Restore the block immediately.
   Timeout is UNKNOWN, not proof of failure or success of candle/data rendering.
8. 1440px: chart/ladder side by side; 420px: stacked, no page horizontal overflow.
   Check dark/light and reduced motion with existing theme environment setting.
9. Inspect timing.jsonl; each activation has its own request_id and ticker.
   Server spans: *.connect, *.execute, *.fetch_map, *.close, market.query,
   rs.total, data.total, ui.data_wait, ui.render_build, ui.server_total.
   Browser events: tv.mount, tv.script_load, tv.iframe_created, tv.iframe_load,
   or tv.script_error / tv.timeout. tv.mount_error indicates JS/transport failure.
   Errors in one panel must not suppress other panels or their timing.
10. Stop the smoke server and turn off tracing:

~~~powershell
Remove-Item Env:CHERRYSTOCK_TICKER_TRACE
~~~

JSONL appends only while the environment variable equals 1.
Archive an existing timing.jsonl before a new comparison session; no automatic deletion.
Do not leave instrumentation enabled for routine indefinite operation.

Interpretation:
- ui.data_wait includes worker scheduling + data.total, not network widget load.
- ui.render_build measures Python component construction, not browser paint.
- ui.server_total starts at server handler entry, not the user's physical click.
- Browser duration_ms starts at its own widget mount; clock=browser_since_mount.
  Server elapsed_ms is receipt time from request start. Do not subtract clocks.
- iframe_load is a document lifecycle event, not candle readiness or feed readiness.
- Nested totals/cumulative cProfile times overlap: do not sum them.
- Long *.connect suggests connection/setup overhead; long *.execute points to that
  view/query; rs.total plus hotspot CSV identifies engine/provider call cost;
  long tv.* after quick backend suggests browser/network/vendor investigation.
  These are follow-up directions only; do not tune in this runbook.

## 7. Verdict / rollback / STOP

PASS only after actual browser charts, UI acceptance and local data checks succeed.
KEEP and STOP; do not start tuning without an evidence-backed next task.
FAIL/REGRESSION if ticker/action/color/coverage wrong, popup breaks or timings absent.
BLOCKED if dependency, DB, browser or vendor/network prevents proving the behavior.
Do not report whole feature PASS from the 33 mocked/component checks alone.

On FAIL/BLOCKED stop server, preserve logs, return to the recorded clean branch:
git switch $previousBranch; if originally detached, git switch --detach $previousCommit.
No reset --hard, force push or DB rollback. After a merged release, use a reviewed
revert commit if rollback is needed. Keep evidence under docs/reference/data/**.

Local agent report:

~~~text
SMARTMONEY POPUP FOLLOW-UP
HEAD / branch:
Python / NiceGUI / Browser:
Compile / 33 focused tests:
Ticker coverage/order / bold / action colors / no MA200 / no commas:
Tooltip R/S appearance / hover / focus:
Actual candles MWG / SHS / ACV:
Partial errors / close / rapid switch / external link:
Baseline exit / profile exit:
Slowest non-overlapping backend stages per ticker:
Top R/S call sites (self vs cumulative):
Observed click-to-content / click-to-candles:
Browser tv events / errors:
Desktop / 420px / themes:
Verdict: PASS | FAIL | BLOCKED | REGRESSION
Action: KEEP | ROLLBACK | STOP
Evidence paths:
~~~
