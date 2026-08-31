# CherryStock Theme Architecture

## 1. Context

### Requirement

CherryStock cần thay đổi theme cho toàn bộ application từ một nơi duy nhất thay vì hard-code màu sắc và styling rải rác trong:

- `src/webapp/NiceGUI_chart.py`;
- `src/webapp/NiceGUI_grid.py`;
- `src/Chart/levelLadderChart.py`;
- `src/Chart/plot.py`;
- `src/webapp/app.py`;
- `src/Ults/lstPara.py`.

Theme phải áp dụng thống nhất cho NiceGUI/Quasar, AG Grid, Apache ECharts và `lightweight_charts`.

### Affected domains

- Presentation / Web UI
- Chart rendering
- AG Grid
- Runtime configuration
- Testing / architecture governance

### Source of Truth

`src/Presentation/theme.py` là **Single Source of Truth** cho visual theme của CherryStock.

Không tạo thêm dictionary màu riêng trong page, chart hoặc grid module.

---

## 2. Current Architecture Before Refactor

Trước refactor, `Ults.lstPara.THEME` chứa một phần token nền nhưng nhiều renderer vẫn giữ màu riêng.

Ví dụ các nhóm hard-code trước đây:

- app background / surface / border;
- hover border và AG Grid row hover;
- ECharts tooltip / current price label;
- `lightweight_charts` background, text, legend và selected/hidden state;
- series màu VNINDEX / MA20 / MA50 / MA100 / MA200;
- standalone `webapp/app.py` body background.

Điều này tạo ra nhiều visual Source of Truth và khiến việc đổi theme không thể thực hiện an toàn tại một nơi.

---

## 3. Problem

Các hạn chế chính:

1. Đổi `THEME` không đảm bảo toàn app đổi theo.
2. Component chart có default color riêng nên dễ lệch với NiceGUI.
3. AG Grid sử dụng CSS variable nhưng hover/border vẫn hard-code.
4. `lightweight_charts` dùng màu trực tiếp trong Python và injected JavaScript.
5. Dark mode của NiceGUI đang hard-code `dark=True`.
6. Không có contract để thêm theme mới.
7. Không có validation bảo đảm theme mới đủ token.

---

## 4. Proposed Architecture

### Target flow

```text
CHERRYSTOCK_THEME / DEFAULT_THEME_NAME
                |
                v
      Presentation.theme
      Theme Registry + Proxy
                |
      +---------+----------+------------------+
      |                    |                  |
      v                    v                  v
 NiceGUI/Quasar         AG Grid          Chart renderers
 build_nicegui_css      theme token      ECharts/lightweight
      |                    |                  |
      +--------------------+------------------+
                           |
                           v
                    Page composition
```

### Design principles

- One visual Source of Truth.
- Consumer code uses semantic tokens instead of raw hex values.
- Chart/business calculations remain independent from theme.
- Theme is presentation concern and lives under `src/Presentation`.
- Existing `Ults.lstPara.THEME` remains only as a compatibility alias during migration.
- Theme identity colors and semantic state colors are centralized separately by token name.
- V1 theme state is process-wide, not per-user.

---

## 5. Components

## 5.1 `src/Presentation/theme.py`

### Responsibility

Own:

- theme registry;
- default theme;
- environment override;
- current theme;
- validation of required tokens;
- semantic token proxy;
- NiceGUI/Quasar/AG Grid global CSS.

### Inputs

- `CHERRYSTOCK_THEME` environment variable, optional;
- explicit theme name passed to `get_theme()` or `set_theme()`.

### Outputs

- `THEME`: dynamic Mapping proxy;
- `get_theme()`;
- `get_theme_name()`;
- `set_theme()`;
- `available_themes()`;
- `is_dark_theme()`;
- `build_nicegui_css()`;
- `get_ag_grid_theme()`.

### State

Process-local selected theme name.

No database persistence in V1.

### Failure behavior

Unknown theme name raises `ValueError`.

Theme definition missing a required token raises `RuntimeError` during module import, so incomplete themes fail fast.

---

## 5.2 Theme Registry

V1 ships with:

- `cherry_dark` — current CherryStock financial-terminal visual baseline;
- `cherry_light` — light-mode equivalent.

Each theme must provide all required semantic tokens.

Core token groups:

| Group | Tokens |
|---|---|
| Surfaces | `background`, `surface`, `surface_alt`, `border` |
| Text | `text`, `muted`, `on_primary` |
| Brand | `primary` |
| State | `positive`, `negative`, `warning` |
| Interaction | `hover_border`, `field_hover`, `grid_row_hover` |
| Chart UI | `tooltip_background`, `current_label_background`, `chart_neutral`, `chart_hidden`, `chart_selection_background` |
| Market series | `series_vnindex`, `series_btc`, `series_spx`, `series_ma20`... |
| Framework | `ag_grid_theme`, `is_dark` |

---

## 5.3 NiceGUI / Quasar Adapter

`build_nicegui_css()` builds global CSS from the active semantic tokens.

It owns:

- body/page background;
- Quasar primary color;
- dashboard cards;
- tab active background;
- outlined field borders;
- AG Grid CSS variables;
- responsive shared UI rules.

Page modules may still own layout classes such as padding, width, grid columns and breakpoints, but must not introduce new app-theme colors directly.

---

## 5.4 AG Grid Adapter

AG Grid uses:

- `get_ag_grid_theme()` / theme token for the framework base theme;
- CSS variables generated by `build_nicegui_css()`.

Grid modules own:

- columns;
- filters;
- row data;
- behavior.

Grid modules do not own application color definitions.

---

## 5.5 ECharts Adapter

ECharts option builders read `Presentation.theme.THEME` or `get_theme()`.

Examples:

- axis text → `muted`;
- grid line → `border`;
- support → `positive`;
- resistance → `negative`;
- current price → `warning`;
- tooltip background → `tooltip_background`.

A chart may still accept an explicit color override when the color is part of its public rendering contract, but the default must come from the centralized theme.

---

## 5.6 lightweight_charts Adapter

`src/Chart/plot.py` uses centralized tokens for:

- chart background;
- chart text;
- legend text;
- fallback line color;
- selected/hidden legend state;
- default VNINDEX and MA series colors.

Injected JavaScript must receive the values from Python theme tokens instead of embedding additional hard-coded app colors.

---

## 6. Data Flow

At process start:

1. Import `Presentation.theme`.
2. Resolve `CHERRYSTOCK_THEME`.
3. Validate selected name against registry.
4. Validate every registered theme has required tokens.
5. Set process-wide current theme.

At page render:

1. `build_page()` reads `THEME`.
2. `ui.colors(primary=...)` uses `primary`.
3. `build_nicegui_css()` injects shared CSS.
4. NiceGUI component classes use active semantic tokens.
5. AG Grid consumes shared CSS variables.
6. ECharts option builders read the same theme proxy.
7. `lightweight_charts` initializers read the same theme proxy.
8. `ui.run(dark=is_dark_theme())` aligns Quasar dark mode with the active theme.

---

## 7. Contracts

### Theme name contract

```text
[a-z][a-z0-9_]*
```

Examples:

- `cherry_dark`
- `cherry_light`
- future: `bloomberg_dark`

### Runtime configuration

PowerShell:

```powershell
$env:CHERRYSTOCK_THEME = "cherry_light"
python src/webapp/NiceGUI_chart.py
```

Default:

```text
DEFAULT_THEME_NAME = "cherry_dark"
```

### Consumer contract

Preferred:

```python
from Presentation.theme import THEME

color = THEME["primary"]
```

For reusable builders:

```python
from Presentation.theme import get_theme

tokens = get_theme()
```

Do not:

```python
color = "#38bdf8"
```

when the value represents an application theme semantic.

---

## 8. Theme vs Business/Data Identity

Not every color is presentation state.

A color may represent:

1. **Theme semantic** — background, positive, negative, warning, border.
2. **Data identity** — VNINDEX, BTC, Gold, MA20, MA200.

Both are centralized in V1 because users expect a complete visual switch, but they remain named separately so future themes can preserve or alter data identity intentionally.

Business calculations must never depend on a visual color token.

---

## 9. Compatibility & Migration

### Backward compatibility

`Ults.lstPara.THEME` remains a compatibility alias pointing to `Presentation.theme.THEME`.

This prevents breaking older modules while new/refactored presentation modules import directly from `Presentation.theme`.

### Migration order

1. Add centralized theme registry.
2. Add compatibility alias.
3. Move NiceGUI global CSS to `build_nicegui_css()`.
4. Refactor ECharts defaults.
5. Refactor AG Grid theme name / semantic colors.
6. Refactor `lightweight_charts`.
7. Refactor standalone web page.
8. Add tests.
9. Remove compatibility alias only after repository-wide consumers no longer use it.

---

## 10. Runtime Theme Switching

V1 guarantees **centralized app-wide theme selection on process/page startup**.

`set_theme()` changes the process-wide theme used by future renders, but existing browser DOM, already-created ECharts instances and iframe charts must be refreshed/rebuilt.

A future V2 may add a header theme selector with:

- per-session selected theme;
- localStorage persistence;
- CSS variable swap;
- controlled rerender of ECharts and iframe chart components.

Per-user runtime theme is intentionally not implemented in V1 because a global process variable would leak one user's selection into other sessions.

---

## 11. Validation & Testing

Required tests:

- both built-in themes are registered;
- every theme contains all required tokens;
- invalid theme names fail clearly;
- `set_theme()` changes `THEME` proxy values;
- dark/light mode flag is correct;
- generated NiceGUI CSS contains active theme values.

Implementation validation should also verify:

- `NiceGUI_chart.py` imports successfully;
- R/S chart default colors resolve from theme;
- AG Grid renders with dashboard theme CSS;
- `cherry_dark` preserves the current baseline;
- `cherry_light` changes body, cards, grids and chart defaults coherently.

---

## 12. Adding a New Theme

Add one entry to `THEMES` in `src/Presentation/theme.py`.

Example:

```python
THEMES["terminal_blue"] = {
    "name": "terminal_blue",
    "is_dark": True,
    # every required semantic token...
}
```

Do not modify page/chart modules merely to add a new theme.

The import-time validation will reject incomplete definitions.

---

## 13. Observability

At startup or diagnostics, callers can use:

```python
from Presentation.theme import get_theme_name

print(get_theme_name())
```

Future logging may include active theme name in app startup logs.

---

## 14. ADR

**Required.**

This change creates a new cross-module presentation Source of Truth and changes dependency ownership across Web UI, AG Grid and chart renderers.

See [[../adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]].

---

## 15. Related Documents

- [[Chart_Architecture|Chart Architecture]]
- [[RS_Ladder|RS Ladder Architecture]]
- [[../adr/ADR-003-centralized-theme-system|ADR-003 Centralized Theme System]]
- [[../00_HOME|Knowledge Home]]
