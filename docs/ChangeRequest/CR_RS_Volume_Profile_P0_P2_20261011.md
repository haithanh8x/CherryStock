# CR — R/S Volume Profile P0–P2 (2026-10-11)

- **Change:** R/S Volume Profile evidence quality, UI explainability, intraday research and ablation tooling
- **Status:** IMPLEMENTED_PENDING_VALIDATION
- **Owner:** General Coding → Test Engineer
- **Primary scope:** RS-01…RS-06 (P0, P1, P2)
- **Default runtime behavior:** unchanged (EOD profile, LEGACY volume confirmation)
- **Model promotion:** NOT APPROVED; requires local point-in-time OOS evaluation
- **Source architecture:** `docs/architecture/RS_Ladder.md`, ADR-006
- **Runbook:** `docs/runbook/RS_Volume_Profile_P0_P2.md`

## Implementation

- P0: strictly finite OHLCV daily input; source-resolution metadata; new optional distance-aware VP scorer with overlap discount (no POC/HVN/LVN multi-node sum); signed marginal Strength explanation carried to ranked levels.
- P1: Level Details expands Volume Profile details without additional DB reads; research comparison of persisted validation/test events with hold/break/retest and sample-coverage diagnostics.
- P2: opt-in intraday bars from `raw_stock_intraday`, cross-checked per trading date against EOD reference volume, with strict `INTRADAY` mode and explicit `AUTO` fallback. Default EOD retained.

## Verification

- GitHub Actions focused compile / test collection / unit suite: [run 38107534104](https://github.com/haithanh8x/CherryStock/actions/runs/38107534104) **SUCCESS** (45 tests across baseline R/S and new VP cases).
- Synthetic unit test coverage includes old baseline behavior, future-data exclusion, volume-mismatch rejection, Opt-in Strength, VP UI contract, and validation/test metrics.
- **Not validated:** real CherryMon intraday completeness, real-data OOS lift, browser-rendered NiceGUI integration and intraday performance. They require local environment and a separate independent Test Engineer verdict.

## Decision / next gate

The implementation is ready for targeted local verification but cannot yet be claimed as a better scoring model. Keep runtime `LEGACY` and `EOD`; do not auto-promote, auto-merge or deploy until the V2.4 evidence gates have passed. See runbook for reproducible commands and explicit criteria.


## RS-02 / RS-05 follow-up — matched evaluation (2026-10-11)

**Status:** IMPLEMENTED_RESEARCH_DIAGNOSTICS; **NOT PROMOTED**.

Local validation results supplied by the operator (not independently replayed from
GitHub): 46 developer tests passed; EOD/intraday preflight passed; four runs
each persisted 233 events / 39 snapshots. Initial unpaired aggregate evidence
`docs/reference/data/rs/volume_profile_ablation_comparison.csv` reports
DISTANCE_AWARE hold delta 0/0 on VALIDATION/TEST, INTRADAY +0.0645/0,
NO_VOLUME +0.0323/-0.0218. None satisfies a positive VALIDATION and
non-negative TEST promotion gate. The original comparison did **not** guarantee
matching event identity and is *not* sufficient for model promotion.

Root-cause/code finding: `score_zones()` changes Strength with the
DISTANCE_AWARE volume discount, but `rank_levels()` selects the nearest R/S by
price; the existing future-outcome evaluator labels the same price levels
independently of Strength. Zero price-level outcome lift is therefore expected
whenever the same levels are selected. This does **not** establish zero score
or zero threshold-80 selection effect.

Implementation for targeted RS-02/RS-05 research:
- Compare persisted events on `Ticker, AsOfDate, Split, LevelRank, LevelType`.
- Price-change/missing/regime-mismatched levels are reported and excluded from
  strictly matched level outcome rates; split/ticker/regime and sample gates
  are explicit.
- Report `StrengthScore` delta, threshold-80 crossings, conditional
  strong-level hold rate and `SCORE_ONLY_NO_OUTCOME_CHANGE` diagnoses.
- Keep original unpaired CSV intact, write separate matched and event-diagnostic
  evidence CSVs when local CherryMon is reachable.
- No NiceGUI visual validation in this follow-up, per requester; prior UI
  implementation remains unverified.

**Remaining gate:** run read-only paired comparator on local CherryMon, review
matched-level coverage, denominators and out-of-sample threshold-calibration
metrics with independent TestEngineer. GitHub CI unit tests alone cannot
produce these real-data artifacts. No changes to EOD/LEGACY defaults and no
merge/deployment approval.

