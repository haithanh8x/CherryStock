# R/S Volume Profile P0–P2: validation and research rollout

Date: 2026-10-11. Owner: General Coding → Test Engineer. Status: **IMPLEMENTED_PENDING_VALIDATION**.
This is a backward-compatible extension to ADR-006 and R/S V2.4. It is **not** a production model promotion.

> **Main branch publication note:** This runbook is available on `main` for review and handoff, but the implementation, new scripts, and tests remain in [draft PR #25](https://github.com/haithanh8x/CherryStock/pull/25) on `feat/rs-volume-profile-p0-p2-20261011`. Check out that feature branch before executing P0–P2 commands. No code or model activation is implied by publishing this document.

## Scope / task mapping

| Task | Delivered | Validation |
|---|---|---|
| RS-01 / P0 | EOD source validation (finite OHLCV, 120 sessions / 48 bins defaults), explicit VP resolution metadata; intraday coverage checks | focused pytest + real data preflight below |
| RS-02 / P0 | `DISTANCE_AWARE` challenger: distance-decayed best VP node, overlap discount when Volume Structure already supports the zone | V2.3/V2.4 OOS ablation; baseline `LEGACY` unchanged |
| RS-03 / P0 | `RankedLevel` retains VP confirmation, node, share, data-resolution and marginal Strength contribution | unit + UI checks |
| RS-04 / P1 | Level Details renders VP evidence, volume-node lineage, share and research source resolution. Existing Strength ≥80 visibility untouched | NiceGUI browser check required |
| RS-05 / P1 | Read-only comparison of persisted V2.3 evaluation events on VALIDATION/TEST splits | local CherryMon runs required |
| RS-06 / P2 | Explicit `EOD`, `INTRADAY`, `AUTO` provider modes; intraday from `raw_stock_intraday`, checked session-wise against EOD volume | local coverage / performance gate required |

## Runtime and data rules

- Default remains `VolumeProfileConfig(source_mode="EOD")` and `StrengthConfig(volume_confirmation_mode="LEGACY")`. **Do not change the default model to the challenger before promotion gates pass**.
- Intraday source: `raw_stock_intraday(DateTime, High, Low, Volume, TickSeq)`; EOD volume reference: `raw_stock_eod(Date, Volume)`. Point-in-time filter `Date <= as_of_date` is applied before any level calculation.
- Eligible intraday session requires its summed `Volume` to equal 85–115% of the corresponding EOD volume (configurable). At least 30 eligible sessions **and ≥90% coverage of the EOD sessions in the selected lookback window** are required. The latest EOD session must also be volume-validated; otherwise INTRADAY fails closed. Missing/incomplete sessions are excluded, not silently treated as full days. No data mutation or schema migration is introduced.
- Intraday is bar-based (High/Low range allocation), **not** tick-accurate. `AUTO` can fall back to EOD only on explicit opt-in; warning and `fallback_reason` are carried in lineage metadata. `INTRADAY` instead raises on inadequate coverage.
- Multiple POC/HVN/LVN nodes share the single `VOLUME_STRUCTURE` family. `DISTANCE_AWARE` chooses one best confirmation per zone and applies `volume_overlap_discount` (default 0.5) when that family is already in the zone.
- `volume_score_contribution` is the change in the normalized final Strength **caused by the matching volume-confirmation term**, and can be negative; it does not mean statistical predictive lift.
- S1/R1 are always the nearest eligible support/resistance regardless of score. Visible levels remain Strength ≥80.

## Focused developer/test verification (repository root)

~~~powershell
python -m pytest tests/test_rs_ladder.py tests/test_rs_evaluation.py tests/test_rs_volume_profile_p0_p2.py tests/test_rs_volume_profile_comparison.py --collect-only -q
python -m pytest tests/test_rs_ladder.py tests/test_rs_evaluation.py tests/test_rs_volume_profile_p0_p2.py tests/test_rs_volume_profile_comparison.py -q
~~~

The matching `.github/workflows/rs-volume-profile-validation.yml` runs focused tests on PR. These are synthetic checks, not real-data certification.

## Real-data preflight — mandatory before any production source switch

1. Run `src/DuckDB/sql/rs_v2_2_preflight.sql` against local CherryMon. Confirm active EOD history and non-null, positive volume for the sampled ticker(s).
2. Compare `SUM(raw_stock_intraday.Volume)` with `raw_stock_eod.Volume` by `Ticker, Date`; inspect session coverage, duplicate `DateTime/TickSeq`, unit consistency and timestamp cutoffs. **If volume is cumulative instead of per bar, stop and repair the data contract**.
3. Compare CPU, memory and query latency for 3 tickers across at least 30 eligible intraday sessions against the EOD default. Reject intraday promotion if coverage/performance are inadequate.
4. Run NiceGUI R/S tab on qualifying ticker, expand R/S → Sources → VP node; check VP score, resolution, share, Strength contribution and warning metadata. Verify empty filters, refresh and a different ticker/date do not show stale values.
5. Verify intraday POC/HVN/LVN point-in-time snapshots and EOD baseline for historical dates, including missing-data behavior.

## Historical evaluation (research only, local CherryMon required)

The existing `scripts/run_rs_v2_3_evaluation.py` **writes research events/metrics** to the local DuckDB repository. It does not promote models. Choose **identical** tickers, date range, horizon and snapshot step for all variants; use a historical window with sufficient point-in-time volume data and TRAIN/VALIDATION/TEST snapshots.

Example (PowerShell from repository root; replace dates/tickers with locally verified coverage):

~~~powershell
$TICKERS = "MWG,FPT,HPG"
$START = "2026-07-01"
$END = "2026-09-30"
$COMMON = @("--tickers",$TICKERS,"--start",$START,"--end",$END,"--snapshot-step","5","--horizon-bars","20")

python scripts/run_rs_v2_3_evaluation.py @COMMON --model-version RS_VP_EOD_BASELINE --run-id vp-eod-baseline-20261011
python scripts/run_rs_v2_3_evaluation.py @COMMON --model-version RS_VP_DROP --run-id vp-no-volume-20261011 --enabled-sources MA,BB,SWING,PREVIOUS_HL,52W_HL,ATR,RSI
python scripts/run_rs_v2_3_evaluation.py @COMMON --model-version RS_VP_DISTANCE --run-id vp-distance-20261011 --strength-config-json '{"volume_confirmation_mode":"DISTANCE_AWARE"}'
python scripts/run_rs_v2_3_evaluation.py @COMMON --model-version RS_VP_INTRADAY --run-id vp-intraday-20261011 --volume-profile-config-json '{"source_mode":"INTRADAY"}'

python scripts/compare_rs_volume_profile.py --baseline-run-id vp-eod-baseline-20261011 --challenger-run-ids vp-no-volume-20261011,vp-distance-20261011,vp-intraday-20261011 --strong-threshold 80
~~~

If the intraday candidate has insufficient 30-session EOD-matched warm-up at any sampled date, stop that variant rather than inventing intraday evidence. Prefer a later verified period or keep the P2 runtime disabled. Set unique `--run-id` on each rerun; preserve version/config signature lineage.

The comparison summarizes:

- touch count and sample/snapshot coverage;
- `hold_after_touch` (bounce/hold proxy);
- `break_after_touch` (break rate conditional on touch);
- `retest_after_break` (**not** an actual false-breakout label);
- validation/test marginal deltas versus baseline.

Assess by ticker, market regime and multiple horizons through the existing R/S V2.4 Source Effectiveness framework. A real false-breakout outcome needs a separate explicit recross-and-hold labeling contract; do not mislabel the retest metric.

**Acceptance / promotion gate:** same eligible timestamps, positive VALIDATION lift, non-negative TEST lift, adequate sample size, stable regimes and no material quality loss. A local Test Engineer must issue PASS/FAIL. V2.4 promotion approval is non-deploying. This feature must remain research-only until separate approval/PR authorizes switching runtime defaults.

## RS-02 + RS-05 follow-up (2026-10-11; score-aware paired ablation)

The initial four persisted runs used 233 events / 39 snapshots each. The original
`docs/reference/data/rs/volume_profile_ablation_comparison.csv` is **UNPAIRED**
aggregate evidence: it checked only counts of ticker/date snapshots, not matching
individual levels. Its observed `DISTANCE_AWARE` delta_hold was zero in both
VALIDATION and TEST, but this is **not sufficient to assert the challenger scoring
does nothing**.

### Root-cause contract (RS-02)

`rank_levels()` ranks R/S by **nearest price** and does not select levels by
Strength. `evaluate_ladder_result()` labels future touches/holds of these
levels, independent of their Strength. `DISTANCE_AWARE` adjusts score and
double-counting discount, **not the level geometry**. If the same levels are
selected, the hold/break/retest labels are identical by construction. Keep the
nearest-price runtime contract unchanged; do **not** force a score-based
re-ranking solely to improve backtest statistics.

### New paired analysis (RS-05)

Run from the feature branch after confirming that all four run IDs still exist
in local CherryMon:

~~~powershell
python scripts/compare_rs_volume_profile.py --baseline-run-id vp-eod-baseline-20261011 --challenger-run-ids vp-no-volume-20261011,vp-distance-20261011,vp-intraday-20261011 --strong-threshold 80 --price-tolerance-pct 0.005
~~~

Read-only database access. It produces **new** reports, preserving the original
unpaired evidence CSV:

- `docs/reference/data/rs/volume_profile_ablation_matched.csv`: paired
  VALIDATION/TEST metrics, baseline-relative deltas, threshold-80 conditional
  hold rates, Strength-to-hold discrimination AUC, exact snapshot coverage, matching/changed-level counts, broken
  out by ALL, TICKER and REGIME.
- `docs/reference/data/rs/volume_profile_level_diagnostics.csv`: one row per
  union event identity (ticker, date, split, level rank and level type).
  Includes prices, Strength, Strength delta, threshold crossings, outcome
  consistency and the diagnosis `SCORE_ONLY_NO_OUTCOME_CHANGE` versus
  `PRICE_CHANGED` / missing event.

`matched_level` requires the same event identity, stable source-independent
regime and price difference <=0.5% by default. Price-shifted or missing levels
are **reported but excluded from paired-outcome rates**; the result explicitly
marks `paired_evidence_eligible=False` and `promotion_evidence_eligible=False`. This is not permission to ignore
new/removed levels: they need a separate level-selection evaluation. No
identical `Ticker/AsOfDate` count is treated as proof of identity.

AUC compares the rank-discrimination of point-in-time Strength against held vs failed touched outcomes. It is not a calibrated probability; when only one outcome class exists, AUC is NaN. **Minimum sample gate: 200 VALIDATION / 100 TEST matched events per reporting scope**, and passing that count does not establish promotion approval. The operator's 54-event VALIDATION/TEST splits are below this gate.

`hold_after_touch` has its usual conditional denominator (only touched
levels); a zero denominator is NaN, not a zero return. The threshold-80
subpopulation can differ across variants and is **selection/calibration
evidence**, not a matched treatment effect. It must be evaluated on OOS
data, checked for denominator/sample adequacy, and cannot override the
promotion gate. The event table does not persist a per-level timeframe
dimension; per-timeframe attribution requires a separate source-lineage
contract, not guesses from level rank.

**Scope decision:** no NiceGUI visual test is required for this follow-up;
this does not certify RS-04 UI. Historical rerun and independent TestEngineer
verdict remain outstanding, since remote CherryMon is not accessible in GitHub CI.

## Source of truth and limitations

- Source: `src/calcEngine/volumeProfile.py`, `src/calcEngine/levelLadder.py`.
- Presentation: `src/Chart/levelLadderChart.py` and `src/webapp/NiceGUI_chart.py`.
- Research comparison: `scripts/compare_rs_volume_profile.py`.
- No real market-data backtest or live NiceGUI rendering was executed through the GitHub-only connection. These gates are **BLOCKED on local CherryMon and UI execution** until run and evidenced; do not report them as PASS.
