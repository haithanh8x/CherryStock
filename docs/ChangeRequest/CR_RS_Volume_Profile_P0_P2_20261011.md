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
