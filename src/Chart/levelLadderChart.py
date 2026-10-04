"""Presentation-only helpers for the Support / Resistance Level Ladder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from Presentation.theme import get_theme
except ModuleNotFoundError:
    from src.Presentation.theme import get_theme

MIN_DISPLAY_STRENGTH_SCORE = 80.0


if TYPE_CHECKING:
    try:
        from calcEngine.levelLadder import LevelLadderResult, RankedLevel
    except ModuleNotFoundError:
        from src.calcEngine.levelLadder import LevelLadderResult, RankedLevel


def _format_price(value: float) -> str:
    return f"{value:,.1f}"


def _level_label(level: "RankedLevel") -> str:
    sign = "+" if level.distance_pct > 0 else ""
    return (
        f"{level.rank}  {_format_price(level.price)}  "
        f"({sign}{level.distance_pct:.2f}%)  Strength {level.strength_score:.0f}"
    )


def ladder_rows(ladder: "LevelLadderResult") -> list[dict[str, Any]]:
    """Return table-ready rows without querying DB or recalculating ladder logic."""
    rows: list[dict[str, Any]] = []
    levels = [
        level
        for level in [*reversed(ladder.resistance_levels), *ladder.support_levels]
        if level.strength_score >= MIN_DISPLAY_STRENGTH_SCORE
    ]
    for level in levels:
        timeframes = sorted(
            {source.timeframe for source in level.sources if source.timeframe},
            key=lambda value: {"M": 0, "W": 1, "D": 2}.get(value, 9),
        )
        rows.append(
            {
                "rank": level.rank,
                "type": level.level_type,
                "price": level.price,
                "zone": (
                    _format_price(level.price)
                    if level.price_low == level.price_high
                    else f"{_format_price(level.price_low)} - {_format_price(level.price_high)}"
                ),
                "distance_pct": round(level.distance_pct, 2),
                "strength": round(level.strength_score, 1),
                "source_count": level.source_count,
                "source_family_count": level.source_family_count,
                "families": ", ".join(sorted({source.source_family for source in level.sources})),
                "timeframes": "/".join(timeframes),
                "sources": ", ".join(source.source_code for source in level.sources),
            }
        )
    return rows


def ladder_tree_nodes(ladder: "LevelLadderResult") -> list[dict[str, Any]]:
    """Return collapsible level/source nodes; no DB reads or score recalculation.

    Roots follow ladder_rows ordering/filtering. IDs are unique per result, and
    optional source values remain unavailable (—) rather than becoming zero.
    """
    levels = [
        level
        for level in [*reversed(ladder.resistance_levels), *ladder.support_levels]
        if level.strength_score >= MIN_DISPLAY_STRENGTH_SCORE
    ]
    nodes: list[dict[str, Any]] = []
    for index, (level, row) in enumerate(zip(levels, ladder_rows(ladder), strict=True)):
        node_id = f"level-{index}-{level.rank}"
        source_nodes = []
        for source_index, source in enumerate(level.sources):
            source_id = f"{node_id}-source-{source_index}"
            details = [
                ("Family", source.source_family),
                ("Type / role", f"{source.source_type} / {source.source_role}"),
                ("Config", source.config_code),
                ("Config ID", source.config_id),
                ("Component", source.component_code),
                ("Weight", f"{source.weight:.2f}"),
                ("Source date", source.source_date.isoformat() if source.source_date else None),
                ("Confirmed at", source.confirmed_at.isoformat() if source.confirmed_at else None),
            ]
            source_nodes.append(
                {
                    "id": source_id,
                    "label": (
                        f"{source.source_code} · {source.timeframe or '—'} · "
                        f"{_format_price(source.price)}"
                    ),
                    "children": [
                        {
                            "id": f"{source_id}-detail-{detail_index}",
                            "label": f"{name}: {value if value is not None else '—'}",
                        }
                        for detail_index, (name, value) in enumerate(details)
                    ],
                }
            )
        nodes.append(
            {
                "id": node_id,
                "label": _level_label(level),
                "is_level": True,
                "rank": row["rank"],
                "level_type": row["type"],
                "price_label": _format_price(row["price"]),
                "distance_label": f"{row['distance_pct']:+.2f}%",
                "strength_label": f"{row['strength']:.1f}",
                "children": [
                    {"id": f"{node_id}-zone", "label": f"Zone: {row['zone']}"},
                    {"id": f"{node_id}-tf", "label": f"Timeframes: {row['timeframes'] or '—'}"},
                    {
                        "id": f"{node_id}-families",
                        "label": f"Families ({row['source_family_count']}): {row['families'] or '—'}",
                    },
                    {
                        "id": f"{node_id}-sources",
                        "label": f"Sources ({row['source_count']})",
                        "children": source_nodes,
                    },
                ],
            }
        )
    return nodes


def empty_level_ladder_chart_options(message: str = "Chưa có dữ liệu R/S") -> dict[str, Any]:
    theme = get_theme()
    return {
        "backgroundColor": "transparent",
        "title": {
            "text": message,
            "left": "center",
            "top": "middle",
            "textStyle": {"color": theme["muted"], "fontSize": 14, "fontWeight": "normal"},
        },
        "xAxis": {"show": False},
        "yAxis": {"show": False},
        "series": [],
    }


def build_level_ladder_chart_options(
    ladder: "LevelLadderResult",
    *,
    support_color: str | None = None,
    resistance_color: str | None = None,
    current_color: str | None = None,
    text_color: str | None = None,
    muted_color: str | None = None,
    grid_color: str | None = None,
) -> dict[str, Any]:
    """Build ECharts options from a chart-ready LevelLadderResult only."""
    theme = get_theme()
    support_color = support_color or theme["positive"]
    resistance_color = resistance_color or theme["negative"]
    current_color = current_color or theme["warning"]
    text_color = text_color or theme["text"]
    muted_color = muted_color or theme["muted"]
    grid_color = grid_color or theme["border"]

    support_levels = [
        level
        for level in ladder.support_levels
        if level.strength_score >= MIN_DISPLAY_STRENGTH_SCORE
    ]
    resistance_levels = [
        level
        for level in ladder.resistance_levels
        if level.strength_score >= MIN_DISPLAY_STRENGTH_SCORE
    ]
    all_ranked = [*ladder.support_levels, *ladder.resistance_levels]
    if not all_ranked:
        return empty_level_ladder_chart_options("Không có R/S V2.4 level hợp lệ")

    ranked = [*support_levels, *resistance_levels]
    axis_levels = ranked or all_ranked
    prices = [level.price for level in axis_levels] + [ladder.current_price]
    min_price, max_price = min(prices), max(prices)
    span = max(max_price - min_price, ladder.current_price * 0.04)
    padding = span * 0.12
    y_min = max(0.0, min_price - padding)
    y_max = max_price + padding

    supports = [
        {
            "value": [0, level.price],
            "name": _level_label(level),
            "symbolSize": max(16, min(32, 14 + level.source_family_count * 4)),
        }
        for level in support_levels
    ]
    resistances = [
        {
            "value": [0, level.price],
            "name": _level_label(level),
            "symbolSize": max(16, min(32, 14 + level.source_family_count * 4)),
        }
        for level in resistance_levels
    ]
    current_name = f"PRICE  {_format_price(ladder.current_price)}"

    return {
        "backgroundColor": "transparent",
        "animation": False,
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}",
            "backgroundColor": theme["tooltip_background"],
            "borderColor": grid_color,
            "textStyle": {"color": text_color},
        },
        "grid": {"left": 92, "right": 92, "top": 32, "bottom": 34},
        "xAxis": {
            "type": "value",
            "min": -1,
            "max": 1,
            "show": False,
        },
        "yAxis": {
            "type": "value",
            "min": y_min,
            "max": y_max,
            "scale": True,
            "axisLabel": {
                "color": muted_color,
                ":formatter": "value => Math.round(value).toLocaleString('vi-VN')",
            },
            "axisLine": {"show": True, "lineStyle": {"color": grid_color}},
            "splitLine": {"lineStyle": {"color": grid_color, "opacity": 0.45}},
        },
        "series": [
            {
                "name": "Ladder spine",
                "type": "line",
                "data": [[0, y_min], [0, y_max]],
                "symbol": "none",
                "silent": True,
                "lineStyle": {"color": grid_color, "width": 2},
            },
            {
                "name": "Support",
                "type": "scatter",
                "data": supports,
                "symbol": "circle",
                "itemStyle": {"color": support_color},
                "label": {
                    "show": True,
                    "position": "right",
                    "distance": 12,
                    "color": text_color,
                    "fontSize": 12,
                    "formatter": "{b}",
                },
            },
            {
                "name": "Resistance",
                "type": "scatter",
                "data": resistances,
                "symbol": "circle",
                "itemStyle": {"color": resistance_color},
                "label": {
                    "show": True,
                    "position": "right",
                    "distance": 12,
                    "color": text_color,
                    "fontSize": 12,
                    "formatter": "{b}",
                },
            },
            {
                "name": "Current Price",
                "type": "scatter",
                "data": [{"value": [0, ladder.current_price], "symbolSize": 28}],
                "symbol": "diamond",
                "itemStyle": {"color": current_color},
                "label": {"show": False},
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "lineStyle": {"color": current_color, "width": 1, "type": "dashed"},
                    "data": [{"yAxis": ladder.current_price}],
                    "label": {
                        "show": True,
                        "formatter": current_name,
                        "position": "insideStartTop",
                        "distance": 8,
                        "color": current_color,
                        "fontSize": 13,
                        "fontWeight": "bold",
                        "backgroundColor": theme["current_label_background"],
                        "padding": [2, 6],
                        "borderRadius": 3,
                    },
                },
                "z": 5,
            },
        ],
    }
