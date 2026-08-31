"""Centralized presentation theme system for CherryStock.

This module is the Single Source of Truth for app-wide visual tokens used by
NiceGUI, AG Grid, ECharts and lightweight_charts renderers.

The default theme can be changed in one place with DEFAULT_THEME_NAME or at
deployment time through CHERRYSTOCK_THEME.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from typing import Any, Final


ThemeTokens = Mapping[str, Any]

_REQUIRED_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "name",
        "is_dark",
        "background",
        "surface",
        "surface_alt",
        "border",
        "text",
        "muted",
        "primary",
        "positive",
        "negative",
        "warning",
        "hover_border",
        "field_hover",
        "grid_row_hover",
        "tooltip_background",
        "current_label_background",
        "on_primary",
        "chart_neutral",
        "chart_hidden",
        "chart_selection_background",
        "series_vnindex",
        "series_remaining_vnindex",
        "series_btc",
        "series_spx",
        "series_ndx",
        "series_gold",
        "series_oil",
        "series_dxy",
        "series_usdvnd",
        "series_ma20",
        "series_ma50",
        "series_ma100",
        "series_ma200",
        "ag_grid_theme",
    }
)


THEMES: Final[dict[str, dict[str, Any]]] = {
    "cherry_dark": {
        "name": "cherry_dark",
        "is_dark": True,
        "background": "#07111f",
        "surface": "#0f1b2d",
        "surface_alt": "#182D43",
        "border": "#416987",
        "text": "#e5edf7",
        "muted": "#7195B3",
        "primary": "#5B8DB8",
        "positive": "#22c55e",
        "negative": "#ef4444",
        "warning": "#f59e0b",
        "hover_border": "#6FA3CC",
        "field_hover": "#6FA3CC",
        "grid_row_hover": "#1b2a3f",
        "tooltip_background": "#111827",
        "current_label_background": "#0f1b2d",
        "on_primary": "#F1F5F9",
        "chart_neutral": "#ffffff",
        "chart_hidden": "#9aa4b2",
        "chart_selection_background": "#2a2f36",
        "series_vnindex": "#03fd10",
        "series_remaining_vnindex": "#a0aec0",
        "series_btc": "#f7931a",
        "series_spx": "#3182ce",
        "series_ndx": "#00b5d8",
        "series_gold": "#ecc94b",
        "series_oil": "#e53e3e",
        "series_dxy": "#a0aec0",
        "series_usdvnd": "#ffaa00",
        "series_ma20": "#00ff0d",
        "series_ma50": "#a6fcb8",
        "series_ma100": "#fc8b8b",
        "series_ma200": "#fd0303",
        "ag_grid_theme": "quartz",
    },
    "cherry_light": {
        "name": "cherry_light",
        "is_dark": False,
        "background": "#f4f7fb",
        "surface": "#ffffff",
        "surface_alt": "#eef3f8",
        "border": "#cbd5e1",
        "text": "#172033",
        "muted": "#64748b",
        "primary": "#0284c7",
        "positive": "#15803d",
        "negative": "#dc2626",
        "warning": "#b45309",
        "hover_border": "#94a3b8",
        "field_hover": "#64748b",
        "grid_row_hover": "#e2e8f0",
        "tooltip_background": "#ffffff",
        "current_label_background": "#ffffff",
        "on_primary": "#ffffff",
        "chart_neutral": "#172033",
        "chart_hidden": "#64748b",
        "chart_selection_background": "#e2e8f0",
        "series_vnindex": "#16a34a",
        "series_remaining_vnindex": "#64748b",
        "series_btc": "#ea580c",
        "series_spx": "#2563eb",
        "series_ndx": "#0891b2",
        "series_gold": "#ca8a04",
        "series_oil": "#dc2626",
        "series_dxy": "#64748b",
        "series_usdvnd": "#d97706",
        "series_ma20": "#16a34a",
        "series_ma50": "#4ade80",
        "series_ma100": "#f87171",
        "series_ma200": "#dc2626",
        "ag_grid_theme": "quartz",
    },
}


DEFAULT_THEME_NAME: Final[str] = "cherry_dark"


def _resolve_initial_theme_name() -> str:
    requested = os.getenv("CHERRYSTOCK_THEME", DEFAULT_THEME_NAME).strip()
    if requested not in THEMES:
        available = ", ".join(sorted(THEMES))
        raise ValueError(
            f"Unknown CHERRYSTOCK_THEME={requested!r}. Available themes: {available}"
        )
    return requested


for _theme_name, _tokens in THEMES.items():
    missing = _REQUIRED_TOKENS.difference(_tokens)
    if missing:
        raise RuntimeError(
            f"Theme {_theme_name!r} is missing required tokens: {sorted(missing)}"
        )


_current_theme_name = _resolve_initial_theme_name()


def available_themes() -> tuple[str, ...]:
    """Return all registered theme names."""

    return tuple(THEMES)


def get_theme_name() -> str:
    """Return the currently selected app-wide theme name."""

    return _current_theme_name


def get_theme(name: str | None = None) -> ThemeTokens:
    """Return theme tokens for *name* or for the current app-wide theme."""

    theme_name = name or _current_theme_name
    try:
        return THEMES[theme_name]
    except KeyError as exc:
        available = ", ".join(sorted(THEMES))
        raise ValueError(
            f"Unknown theme {theme_name!r}. Available themes: {available}"
        ) from exc


def set_theme(name: str) -> None:
    """Switch the process-wide theme used by future renders.

    Existing browser DOM/ECharts instances must be rebuilt or refreshed to pick
    up the new tokens. V1 intentionally keeps theme state process-wide.
    """

    global _current_theme_name
    if name not in THEMES:
        available = ", ".join(sorted(THEMES))
        raise ValueError(f"Unknown theme {name!r}. Available themes: {available}")
    _current_theme_name = name


def is_dark_theme(name: str | None = None) -> bool:
    """Return whether the selected theme should enable NiceGUI dark mode."""

    return bool(get_theme(name)["is_dark"])


class _ThemeProxy(Mapping[str, Any]):
    """Mapping proxy that always resolves against the current theme."""

    def __getitem__(self, key: str) -> Any:
        return get_theme()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(get_theme())

    def __len__(self) -> int:
        return len(get_theme())

    def __repr__(self) -> str:
        return f"ThemeProxy(name={get_theme_name()!r})"


THEME: Final[Mapping[str, Any]] = _ThemeProxy()


def get_ag_grid_theme(name: str | None = None) -> str:
    """Return the AG Grid base theme configured by the selected theme."""

    return str(get_theme(name)["ag_grid_theme"])


def with_alpha(color: str, alpha: float) -> str:
    """Convert a #RRGGBB color to an rgba() string with *alpha*."""

    value = color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {color!r}")
    if not 0 <= alpha <= 1:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha}")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha:g})"


def build_nicegui_css(theme: ThemeTokens | None = None) -> str:
    """Build global NiceGUI/Quasar/AG Grid CSS from semantic theme tokens."""

    tokens = theme or get_theme()
    return f"""
        :root {{
            --q-primary: {tokens['primary']};
            --cs-background: {tokens['background']};
            --cs-surface: {tokens['surface']};
            --cs-surface-alt: {tokens['surface_alt']};
            --cs-border: {tokens['border']};
            --cs-text: {tokens['text']};
            --cs-muted: {tokens['muted']};
            --cs-positive: {tokens['positive']};
            --cs-negative: {tokens['negative']};
            --cs-warning: {tokens['warning']};
        }}

        body {{
            background: {tokens['background']};
            color: {tokens['text']};
        }}

        .q-page, .q-layout, .nicegui-content {{
            background: {tokens['background']};
        }}

        .nicegui-content {{
            padding: 0 !important;
        }}

        .dashboard-card {{
            overflow: hidden;
            backdrop-filter: blur(12px);
        }}

        .dashboard-card:hover {{
            border-color: {tokens['hover_border']};
        }}

        .metric-card {{
            min-height: 112px;
        }}

        .q-tab {{
            min-height: 46px;
            padding: 0 16px;
        }}

        .q-tab--active {{
            background: {tokens['surface_alt']};
            border-radius: 10px;
        }}

        .q-field--outlined .q-field__control:before {{
            border-color: {tokens['border']};
        }}

        .q-field--outlined:hover .q-field__control:before {{
            border-color: {tokens['field_hover']};
        }}

        .ag-root-wrapper {{
            border-color: {tokens['border']} !important;
            border-radius: 12px !important;
        }}

        .dashboard-data-grid {{
            --ag-background-color: {tokens['surface']};
            --ag-foreground-color: {tokens['text']};
            --ag-header-background-color: {tokens['surface_alt']};
            --ag-header-foreground-color: {tokens['text']};
            --ag-odd-row-background-color: {tokens['surface_alt']};
            --ag-row-hover-color: {tokens['grid_row_hover']};
            --ag-border-color: {tokens['border']};
            --ag-secondary-border-color: {tokens['border']};
        }}

        .timeframe-toggle .q-btn {{
            min-width: 58px;
        }}

        .app-shell {{
            max-width: 2200px;
            margin: 0 auto;
        }}

        @media (max-width: 700px) {{
            .metric-card {{
                min-height: 104px;
            }}

            .timeframe-toggle .q-btn {{
                min-width: 48px;
                padding-left: 8px;
                padding-right: 8px;
            }}
        }}
    """
