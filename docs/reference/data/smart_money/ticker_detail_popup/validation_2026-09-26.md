# SmartMoney Ticker Detail Popup — Validation Evidence

Date: 2026-09-26
Runbook: `docs/runbook/SmartMoney_Ticker_Detail_Popup.md`
Branch: `feature/smartmoney-ticker-detail`
HEAD: `fdb30aa5e4762c37394d39ff8170998aedb2378a`
Implementation commit: `fc7f5bb23ea0d8d7302704fd24dc0a18b1eee231` (ancestor of HEAD)
Python: 3.13.5 (system interpreter)
NiceGUI: server on 127.0.0.1:8081

## 1. Safe sync
- Working tree clean before switch.
- Switched to `feature/smartmoney-ticker-detail` tracking `origin/...`.
- HEAD recorded: `fdb30aa5e4762c37394d39ff8170998aedb2378a`.

## 2. Compile
- `python -m py_compile` on all 8 target modules: exit=0.

## 3. Focused pytest
- 25 passed, exit=0 (contract, dialog, tradingview_links, snapshot_query, state_flow).
- `test_late_result_cannot_replace_new_ticker` passed: slow MWG result cannot overwrite newer FPT popup (generation guard).

## 4. Real-data snapshot
- `validate_smart_money_ui_snapshot.py`: PASS, 347 tickers, 9 buckets, counts stable.
- MWG load: ticker=MWG, market=HSX, sections all 1 row, errors={}, ladder=(MWG, 2026-09-25, 73.4).
- Field counts: SmartMoney=21, Profile=24, Context=44.

## 5. R/S parity vs existing tab
- Popup ladder == `build_level_ladder('MWG', as_of_date=None, cluster_threshold_pct=0.01)`:
  as_of=2026-09-25, price=73.4, S1=71.0765, R1=75.2603, strength=72.5, rr=0.8006. MATCH=True.

## 6. TradingView market mapping
- HSX→HOSE:MWG, HOSE→HOSE:MWG, HNX→HNX:SHS, UPCOM→UPCOM:ACV.
- Missing market → None (no default guess); bad market → None.

## 7. Browser smoke (Chrome via Playwright)
- SmartMoney tab renders state flow + exchange-qualified ticker links.
- Click MWG → popup "MWG · TradingView & phân tích", HOSE:MWG widget, R/S + 3 views.
- SHS → HNX:SHS; ACV → UPCOM:ACV (iframe titles verified).
- R/S in popup: Giá 73.40, Reward/Risk 0.80, date 2026-09-25; S1 price 71.0765 dist -3.17, R1 price 75.2603 dist 2.53 (matches engine; dist already %, not ×100).
- SmartMoney 21 / Profile 24 / Context 44 fields confirmed in DOM.
- Units: ConfidenceScore 97.1354 (not %), DirectionalBias 0.0294 (not %), MedianAbsSwingPct 11.42% (×100), MedianATRNormalizedMove 4.02 lần, CurrentMovePct 7.14%, ReversalFromCandidatePct 0.95%. NULL → "—" (LimitUpScore).
- Separate dates: ContextAsOfDate 2026-09-22, ProfileAsOfConfirmedAtDate 2026-09-17, CurrentLegAsOfDate 2026-09-22; CurrentLegStatus PROVISIONAL.
- Tooltip: Vietnamese label + meaning + "Ví dụ minh họa" (not live quote).
- Hover: pointer + underline + light bg, no size/weight/position change; first two per bucket bold.
- Focus-visible: outline rgb(91,141,184) solid 2px; Enter opens popup; Escape closes.
- Transition: color/background 150ms ease-out; `@media (prefers-reduced-motion: reduce){ .cs-ticker-link{transition:none} }`.
- Ctrl/Cmd-click: JS handler returns early on modifier keys → native `target=_blank` external nav (href/target/rel verified).
- "Mở trên TradingView ↗" link present in popup with correct URL, target=_blank.
- Refresh twice: counts/order/anchors stable (ACCUMULATION 59, etc.).
- Desktop 1440px: chart left + ladder right; 420px: stacked, no horizontal overflow.
- Dark theme active (body--dark, surface rgb(15,27,45), text rgb(229,237,247)); light theme supported via CHERRYSTOCK_THEME.
- Close via Đóng button and Escape: dialog + iframe removed (cleanup verified).
- Missing-market path: code shows market picker (HOSE/HNX/UPCOM) when no resolvable market; no real ticker without market in current data → N/A for real data, covered by code path.

## 8. Server log
- No application errors during smoke. Only expected WatchFiles reload notices and external TradingView widget sandbox/localStorage warnings (external, not CherryStock).

## Verdict
PASS

## Action
KEEP — handoff PR review/merge; STOP.

## Residual notes
- TradingView widget is external; its sandbox emits localStorage/cookie warnings in the browser console. These are external and do not affect CherryStock analytics or the "Mở trên TradingView" fallback link.
- Light theme not visually re-run in this session (server ran default dark); theme variables and `is_dark_theme()` wiring verified in code.