# ADR-003: Centralized Theme System

- Status: Accepted
- Date: 2026-08-31
- Decision owner: CherryStock presentation architecture

## Context

CherryStock visual configuration was distributed across `Ults.lstPara`, NiceGUI page code, AG Grid CSS, ECharts builders, `lightweight_charts` and standalone HTML.

Changing one theme dictionary did not guarantee a consistent app-wide theme.

## Decision

Create `src/Presentation/theme.py` as the Single Source of Truth for presentation theme tokens.

The module owns:

- theme registry;
- active/default theme;
- environment override through `CHERRYSTOCK_THEME`;
- required-token validation;
- shared NiceGUI/Quasar/AG Grid CSS;
- semantic and chart identity colors used by presentation renderers.

Presentation consumers must depend on this module instead of defining duplicate application-theme colors.

`Ults.lstPara.THEME` remains temporarily as a compatibility alias.

## Consequences

### Positive

- App-wide theme changes become centralized.
- Adding a new theme does not require editing each chart/page.
- Incomplete themes fail fast.
- Dark/light NiceGUI mode can follow theme metadata.
- Visual Source of Truth is explicit.

### Trade-offs

- Theme state in V1 is process-wide.
- Already-rendered ECharts/iframe content must be rebuilt after `set_theme()`.
- Some legacy consumers may temporarily continue importing the compatibility alias.

## Rejected alternatives

### Keep THEME in `Ults.lstPara`

Rejected because `lstPara` is a generic configuration module and cannot cleanly own renderer adapters or presentation contracts.

### Put theme under `src/webapp`

Rejected because `src/Chart` would then depend upward on a page/application package.

### Let each renderer own its own theme

Rejected because it recreates multiple visual Sources of Truth.

## Follow-up

A future ADR is required if CherryStock moves from process-wide theme selection to per-user/session persisted theme state.
