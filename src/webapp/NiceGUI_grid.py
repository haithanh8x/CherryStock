from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Hashable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable

import pandas as pd
from nicegui import ui


GridOptions = dict[str, Any]
FieldConfig = Mapping[str, Any]
FilterConfig = Mapping[str, Any]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GRID_STATE_CACHE_PATH = Path(
    os.getenv(
        "CHERRYSTOCK_GRID_STATE_CACHE",
        str(_PROJECT_ROOT / "Build" / "cache" / "stock_screener_grid_state.json"),
    )
)
_GRID_STATE_CACHE_VERSION = 2
_GRID_STATE_CACHE_MAX_SESSIONS = 200
_GRID_STATE_CACHE_LOCK = RLock()
_GRID_SESSION_STORAGE_KEY = "cherrystock.stock_screener.session_id"

_FIELD_CONFIG_META_KEYS = {"display", "analysis_group"}

_GROUP_LABELS = {
    "GENERAL": "Thông tin chung",
    "FA": "FA — Fundamental Analysis",
    "TA": "TA — Technical Analysis",
    "OTHER": "Khác",
}
_GROUP_ORDER = ("GENERAL", "FA", "TA", "OTHER")

_GENERAL_FIELDS = {
    "ticker",
    "stock",
    "company name",
    "company_name",
    "full name",
    "fullname",
    "industry",
    "industrycode",
    "industry code",
    "sector",
    "market",
    "status",
    "watchlist",
    "ecosystem",
    "date",
    "date/time",
}

_FA_KEYWORDS = (
    "capital",
    "market cap",
    "shares",
    "eps",
    "p/e",
    "pe",
    "p/b",
    "pb",
    "book value",
    "bvps",
    "roa",
    "roe",
    "revenue",
    "profit",
    "income",
    "margin",
    "asset",
    "debt",
    "equity",
    "cash",
    "ebit",
    "ebitda",
    "dividend",
    "yield",
    "expected price",
)

_TA_KEYWORDS = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "openint",
    "ma20",
    "ma50",
    "ma100",
    "ma200",
    "sma",
    "ema",
    "rsi",
    "macd",
    "atr",
    "adx",
    "boll",
    "bbands",
    "stoch",
    "cci",
    "roc",
    "momentum",
    "obv",
    "trend",
    "return",
    "change",
    "price",
)


def _configure_aggrid_enterprise() -> None:
    """Dùng Enterprise bundle để có Columns Tool Panel, grouping và pivot."""
    version = getattr(ui.aggrid, "VERSION", None)
    if not version:
        return

    module_url = os.getenv(
        "AG_GRID_ENTERPRISE_MODULE_URL",
        f"https://cdn.jsdelivr.net/npm/ag-grid-enterprise@{version}/+esm",
    )
    ui.aggrid.set_module_source(module_url)


_configure_aggrid_enterprise()


def dataframe_to_records(df: pd.DataFrame) -> list[dict[Hashable, Any]]:
    """Chuyển DataFrame thành rowData an toàn cho AG Grid."""
    return (
        df.astype(object)
        .where(df.notna(), None)
        .to_dict("records")
    )


def _resolve_field_name(df: pd.DataFrame, field_name: str) -> Hashable | None:
    """Tìm tên cột không phân biệt chữ hoa/chữ thường."""
    if field_name in df.columns:
        return field_name

    normalized_name = field_name.casefold()
    return next(
        (
            column
            for column in df.columns
            if str(column).casefold() == normalized_name
        ),
        None,
    )


def _default_column_def(df: pd.DataFrame, column: Hashable) -> GridOptions:
    """Sinh cấu hình mặc định theo dtype của cột."""
    series = df[column]
    field_name = str(column)

    column_def: GridOptions = {
        "field": field_name,
        "colId": field_name,
        "headerName": field_name.replace("_", " "),
        "sortable": True,
        "resizable": True,
        "minWidth": 70,
    }

    if pd.api.types.is_bool_dtype(series):
        column_def.update(
            {
                "filter": "agTextColumnFilter",
                "width": 100,
                "enableRowGroup": True,
                "enablePivot": True,
            }
        )
    elif pd.api.types.is_numeric_dtype(series):
        column_def.update(
            {
                "filter": "agNumberColumnFilter",
                "type": "numericColumn",
                "width": 110,
                "enableValue": True,
                "defaultAggFunc": "avg",
                "allowedAggFuncs": ["avg", "sum", "min", "max", "count"],
            }
        )
    elif pd.api.types.is_datetime64_any_dtype(series):
        column_def.update(
            {
                "filter": "agDateColumnFilter",
                "width": 140,
                "enableRowGroup": True,
                "enablePivot": True,
            }
        )
    else:
        column_def.update(
            {
                "filter": "agTextColumnFilter",
                "width": 160,
                "enableRowGroup": True,
                "enablePivot": True,
            }
        )

    return column_def


def _aggrid_config(field_config: FieldConfig) -> dict[str, Any]:
    return {
        key: value
        for key, value in field_config.items()
        if key not in _FIELD_CONFIG_META_KEYS
    }


def create_column_defs(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig] | None = None,
) -> list[GridOptions]:
    """Sinh columnDefs phẳng; giữ API cũ cho các grid không dùng tool panel."""
    if field_configs is None:
        requested_configs: list[tuple[str, FieldConfig]] = [
            (str(column), {})
            for column in df.columns
        ]
    else:
        requested_configs = list(field_configs.items())

    column_defs: list[GridOptions] = []

    for requested_field, field_config in requested_configs:
        if not bool(field_config.get("display", True)):
            continue

        actual_column = _resolve_field_name(df, requested_field)
        if actual_column is None:
            continue

        column_def = _default_column_def(df, actual_column)
        column_def.update(_aggrid_config(field_config))
        column_def["resizable"] = True
        column_defs.append(column_def)

    return column_defs


def _field_configs_by_actual_column(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig],
) -> dict[str, FieldConfig]:
    resolved: dict[str, FieldConfig] = {}
    for requested_field, field_config in field_configs.items():
        actual_column = _resolve_field_name(df, requested_field)
        if actual_column is not None:
            resolved[str(actual_column)] = field_config
    return resolved


def _default_visible_columns(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig],
) -> list[str]:
    if not field_configs:
        return [str(column) for column in df.columns]

    visible_columns: list[str] = []
    for requested_field, field_config in field_configs.items():
        if not bool(field_config.get("display", True)):
            continue
        actual_column = _resolve_field_name(df, requested_field)
        if actual_column is not None:
            visible_columns.append(str(actual_column))
    return visible_columns


def _analysis_group(field_name: str, field_config: FieldConfig) -> str:
    explicit_group = str(field_config.get("analysis_group", "")).strip().upper()
    if explicit_group in _GROUP_LABELS:
        return explicit_group

    normalized = field_name.casefold().strip()
    if normalized in _GENERAL_FIELDS:
        return "GENERAL"
    if any(keyword in normalized for keyword in _TA_KEYWORDS):
        return "TA"
    if any(keyword in normalized for keyword in _FA_KEYWORDS):
        return "FA"
    return "OTHER"


def _ordered_columns(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig],
) -> list[Hashable]:
    ordered: list[Hashable] = []
    seen: set[str] = set()

    for requested_field in field_configs:
        actual_column = _resolve_field_name(df, requested_field)
        if actual_column is None:
            continue
        field_name = str(actual_column)
        if field_name in seen:
            continue
        ordered.append(actual_column)
        seen.add(field_name)

    for column in df.columns:
        field_name = str(column)
        if field_name in seen:
            continue
        ordered.append(column)
        seen.add(field_name)

    return ordered


def _create_grouped_column_defs(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig],
    visible_columns: list[str],
) -> list[GridOptions]:
    """Tạo hierarchy General / FA / TA / Other cho Columns Tool Panel."""
    config_by_column = _field_configs_by_actual_column(df, field_configs)
    visible_set = set(visible_columns)
    grouped_children: dict[str, list[GridOptions]] = {
        group_name: []
        for group_name in _GROUP_ORDER
    }

    for column in _ordered_columns(df, field_configs):
        field_name = str(column)
        field_config = config_by_column.get(field_name, {})

        column_def = _default_column_def(df, column)
        column_def.update(_aggrid_config(field_config))

        # Stock Screener ưu tiên manual sizing. Flex có thể co giãn lại theo viewport,
        # vì vậy loại flex khỏi grid này và chuyển sang width cố định ban đầu.
        flex_value = column_def.pop("flex", None)
        column_def.pop("maxWidth", None)
        column_def["resizable"] = True
        if "width" not in column_def:
            configured_min = int(column_def.get("minWidth", 140) or 140)
            column_def["width"] = max(configured_min, 160 if flex_value else 110)

        column_def["hide"] = field_name not in visible_set
        group_name = _analysis_group(field_name, field_config)
        grouped_children[group_name].append(column_def)

    return [
        {
            "headerName": _GROUP_LABELS[group_name],
            "groupId": f"cherrystock_{group_name.casefold()}",
            "marryChildren": False,
            "children": grouped_children[group_name],
        }
        for group_name in _GROUP_ORDER
        if grouped_children[group_name]
    ]


def _stop_parent_swipe(element: Any) -> None:
    """Không cho gesture trong AG Grid nổi lên QTabPanels swipe handler."""
    swipe_events = (
        "touchstart",
        "touchmove",
        "touchend",
        "touchcancel",
        "mousedown",
        "mousemove",
        "mouseup",
        "mouseleave",
        "pointerdown",
        "pointermove",
        "pointerup",
        "pointercancel",
    )
    for event_name in swipe_events:
        element.on(
            event_name,
            js_handler="(event) => event.stopPropagation()",
        )


def _install_global_tab_swipe_blocker() -> None:
    """Chặn swipe navigation của QTabPanels nhưng giữ hành vi của child."""
    ui.add_head_html(
        """
        <script>
        (() => {
            if (window.__cherryStockTabSwipeBlockerInstalled) return;
            window.__cherryStockTabSwipeBlockerInstalled = true;

            const eventNames = [
                'touchstart', 'touchmove', 'touchend', 'touchcancel',
                'mousedown', 'mousemove', 'mouseup', 'mouseleave',
                'pointerdown', 'pointermove', 'pointerup', 'pointercancel'
            ];

            const protectPanel = (panel) => {
                if (!panel || panel.dataset.cherryStockNoSwipe === '1') return;
                panel.dataset.cherryStockNoSwipe = '1';
                eventNames.forEach((eventName) => {
                    panel.addEventListener(
                        eventName,
                        (event) => event.stopPropagation(),
                        false,
                    );
                });
            };

            const protectAll = () => {
                document.querySelectorAll('.q-tab-panel').forEach(protectPanel);
            };

            protectAll();
            new MutationObserver(protectAll).observe(document.documentElement, {
                childList: true,
                subtree: true,
            });
        })();
        </script>
        """
    )


_install_global_tab_swipe_blocker()


# =============================================================================
# Persistent cache: session state + named filter/view presets
# =============================================================================


def _empty_grid_state_cache() -> dict[str, Any]:
    return {
        "version": _GRID_STATE_CACHE_VERSION,
        "sessions": {},
        "saved_filters": {},
        "saved_views": {},
    }


def _normalise_grid_state_cache(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}

    for section in ("sessions", "saved_filters", "saved_views"):
        if not isinstance(data.get(section), dict):
            data[section] = {}

    data["version"] = _GRID_STATE_CACHE_VERSION
    return data


def _read_grid_state_cache_unlocked() -> dict[str, Any]:
    if not _GRID_STATE_CACHE_PATH.exists():
        return _empty_grid_state_cache()

    try:
        data = json.loads(_GRID_STATE_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_grid_state_cache()

    return _normalise_grid_state_cache(data)


def _write_grid_state_cache_unlocked(cache: dict[str, Any]) -> None:
    _GRID_STATE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _GRID_STATE_CACHE_PATH.with_suffix(
        _GRID_STATE_CACHE_PATH.suffix + ".tmp"
    )
    temp_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(_GRID_STATE_CACHE_PATH)


def _read_grid_state_cache() -> dict[str, Any]:
    with _GRID_STATE_CACHE_LOCK:
        return _read_grid_state_cache_unlocked()


def _mutate_grid_state_cache(mutator: Callable[[dict[str, Any]], None]) -> None:
    """Read-modify-write nguyên tử trong process để nhiều session không ghi đè nhau."""
    with _GRID_STATE_CACHE_LOCK:
        cache = _read_grid_state_cache_unlocked()
        mutator(cache)
        _write_grid_state_cache_unlocked(cache)


def _load_session_grid_state(session_id: str) -> dict[str, Any] | None:
    cache = _read_grid_state_cache()
    session_state = cache.get("sessions", {}).get(session_id)
    return session_state if isinstance(session_state, dict) else None


def _save_session_grid_state(
    *,
    session_id: str,
    grid_state: dict[str, Any],
    selected_columns: list[str],
    filter_values: dict[str, list[Any]],
) -> None:
    def mutate(cache: dict[str, Any]) -> None:
        sessions = cache.setdefault("sessions", {})
        sessions[session_id] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "selected_columns": selected_columns,
            "filter_values": filter_values,
            "grid_state": grid_state,
        }

        if len(sessions) > _GRID_STATE_CACHE_MAX_SESSIONS:
            ordered_session_ids = sorted(
                sessions,
                key=lambda item: str(sessions[item].get("updated_at", "")),
            )
            remove_count = len(sessions) - _GRID_STATE_CACHE_MAX_SESSIONS
            for stale_session_id in ordered_session_ids[:remove_count]:
                sessions.pop(stale_session_id, None)

    _mutate_grid_state_cache(mutate)


def _preset_section(kind: str) -> str:
    if kind == "filter":
        return "saved_filters"
    if kind == "view":
        return "saved_views"
    raise ValueError(f"Preset kind không hợp lệ: {kind}")


def _normalise_preset_name(name: Any) -> str:
    return " ".join(str(name or "").strip().split())[:80]


def _list_named_presets(kind: str) -> list[str]:
    section = _preset_section(kind)
    presets = _read_grid_state_cache().get(section, {})
    if not isinstance(presets, dict):
        return []
    return sorted((str(name) for name in presets), key=str.casefold)


def _load_named_preset(kind: str, name: str) -> dict[str, Any] | None:
    section = _preset_section(kind)
    preset_name = _normalise_preset_name(name)
    preset = _read_grid_state_cache().get(section, {}).get(preset_name)
    return preset if isinstance(preset, dict) else None


def _save_named_preset(kind: str, name: str, payload: dict[str, Any]) -> str:
    section = _preset_section(kind)
    preset_name = _normalise_preset_name(name)
    if not preset_name:
        raise ValueError("Tên preset không được để trống")

    def mutate(cache: dict[str, Any]) -> None:
        presets = cache.setdefault(section, {})
        presets[preset_name] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }

    _mutate_grid_state_cache(mutate)
    return preset_name


def _delete_named_preset(kind: str, name: str) -> bool:
    section = _preset_section(kind)
    preset_name = _normalise_preset_name(name)
    deleted = False

    def mutate(cache: dict[str, Any]) -> None:
        nonlocal deleted
        presets = cache.setdefault(section, {})
        deleted = presets.pop(preset_name, None) is not None

    _mutate_grid_state_cache(mutate)
    return deleted


async def _get_or_create_grid_session_id() -> str:
    session_id = await ui.run_javascript(
        f"""
        const key = {json.dumps(_GRID_SESSION_STORAGE_KEY)};
        let sessionId = sessionStorage.getItem(key);
        if (!sessionId) {{
            sessionId = (crypto && crypto.randomUUID)
                ? crypto.randomUUID()
                : `${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
            sessionStorage.setItem(key, sessionId);
        }}
        return sessionId;
        """
    )
    return str(session_id)


def _selected_columns_from_column_state(
    column_state: list[dict[str, Any]] | None,
) -> list[str]:
    if not column_state:
        return []

    selected: list[str] = []
    for item in column_state:
        col_id = item.get("colId")
        if not col_id:
            continue

        is_selected = (
            not bool(item.get("hide", False))
            or bool(item.get("rowGroup", False))
            or bool(item.get("pivot", False))
            or item.get("aggFunc") is not None
        )
        if is_selected:
            selected.append(str(col_id))

    return selected


# =============================================================================
# Generic grid options
# =============================================================================


def create_aggrid_options(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig] | None = None,
    pagination_page_size: int = 20,
) -> GridOptions:
    """Tạo options cho NiceGUI AG Grid."""
    return {
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
            "floatingFilter": True,
        },
        "columnDefs": create_column_defs(
            df=df,
            field_configs=field_configs,
        ),
        "rowData": dataframe_to_records(df),
        "pagination": True,
        "paginationPageSize": pagination_page_size,
        "animateRows": True,
    }


# =============================================================================
# Stock Screener
# =============================================================================


def create_market_grid(
    df: pd.DataFrame,
    *,
    filter_configs: Mapping[str, FilterConfig] | None = None,
    field_configs: Mapping[str, FieldConfig] | None = None,
    grid_height: str = "1000px",
    pagination_page_size: int = 20,
) -> ui.aggrid:
    """
    Stock Screener với AG Grid Columns Tool Panel + named presets.

    Filter preset:
    - Lưu selector filters phía trên grid.
    - Lưu AG Grid filter model (floating/header filters).

    View preset:
    - Lưu visibility, order, width, pinning và sort trong column state.
    - Lưu Row Group / Values / Pivot columns và Pivot Mode.
    - Không ghi đè bộ lọc khi load view.

    Session state vẫn tự động lưu riêng theo browser tab để refresh/reload giữ
    trạng thái đang làm việc. Named presets dùng chung cho các session.
    """
    field_configs = field_configs or {}
    filter_configs = filter_configs or {}

    valid_filter_fields: list[tuple[str, Hashable]] = []
    missing_fields: list[str] = []

    for requested_field in filter_configs:
        actual_column = _resolve_field_name(df, requested_field)
        if actual_column is None:
            missing_fields.append(requested_field)
        else:
            valid_filter_fields.append((requested_field, actual_column))

    if missing_fields:
        ui.notify(
            f"Không tìm thấy field: {', '.join(missing_fields)}",
            type="warning",
        )

    selectors: dict[Hashable, ui.select] = {}
    default_visible_columns = _default_visible_columns(df, field_configs)

    # -------------------------------------------------------------------------
    # Filter controls
    # -------------------------------------------------------------------------
    with ui.row().classes("w-full items-end gap-3 mb-3 flex-wrap"):
        for requested_field, actual_column in valid_filter_fields:
            distinct_values = (
                df[actual_column]
                .dropna()
                .astype(str)
                .drop_duplicates()
                .sort_values()
                .tolist()
            )

            filter_config = filter_configs.get(requested_field, {})
            label = str(
                filter_config.get(
                    "label",
                    requested_field.replace("_", " "),
                )
            )
            width = str(filter_config.get("width", "w-64"))

            selectors[actual_column] = (
                ui.select(
                    options=distinct_values,
                    label=label,
                    multiple=True,
                    with_input=True,
                    clearable=True,
                )
                .props(
                    "outlined dense options-dense "
                    "use-chips popup-content-class=max-h-80"
                )
                .classes(width)
            )

        reset_button = ui.button(
            "Xóa bộ lọc",
            icon="filter_alt_off",
        ).props("outline dense no-caps")

    # -------------------------------------------------------------------------
    # Named presets toolbar
    # -------------------------------------------------------------------------
    with ui.row().classes(
        "w-full items-end gap-2 mb-4 flex-wrap rounded-xl border p-3"
    ):
        saved_filter_select = (
            ui.select(
                options=_list_named_presets("filter"),
                label="Bộ lọc đã lưu",
                with_input=True,
                clearable=True,
            )
            .props("outlined dense options-dense")
            .classes("w-64")
        )
        load_filter_button = ui.button(
            "Tải bộ lọc",
            icon="filter_alt",
        ).props("outline dense no-caps")
        save_filter_button = ui.button(
            "Lưu bộ lọc",
            icon="bookmark_add",
        ).props("outline dense no-caps")
        delete_filter_button = ui.button(
            icon="delete_outline",
        ).props("flat round dense").tooltip("Xóa bộ lọc đã chọn")

        ui.separator().props("vertical").classes("h-9 mx-1")

        saved_view_select = (
            ui.select(
                options=_list_named_presets("view"),
                label="Saved views",
                with_input=True,
                clearable=True,
            )
            .props("outlined dense options-dense")
            .classes("w-64")
        )
        load_view_button = ui.button(
            "Tải view",
            icon="view_column",
        ).props("outline dense no-caps")
        save_view_button = ui.button(
            "Lưu bộ hiển thị",
            icon="save_as",
        ).props("outline dense no-caps")
        delete_view_button = ui.button(
            icon="delete_outline",
        ).props("flat round dense").tooltip("Xóa view đã chọn")

    # Save dialogs are created once and reused.
    with ui.dialog() as save_filter_dialog:
        with ui.card().classes("w-[420px] max-w-[90vw] p-4"):
            ui.label("Lưu bộ lọc").classes("text-lg font-semibold")
            ui.label(
                "Lưu các selector và filter đang đặt trực tiếp trên AG Grid."
            ).classes("text-xs text-gray-500")
            filter_name_input = ui.input(
                label="Tên bộ lọc",
                placeholder="Ví dụ: VN30 ROE cao",
            ).props("outlined autofocus").classes("w-full")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Hủy", on_click=save_filter_dialog.close).props(
                    "flat no-caps"
                )
                confirm_save_filter_button = ui.button(
                    "Lưu",
                    icon="save",
                ).props("unelevated no-caps")

    with ui.dialog() as save_view_dialog:
        with ui.card().classes("w-[420px] max-w-[90vw] p-4"):
            ui.label("Lưu bộ hiển thị").classes("text-lg font-semibold")
            ui.label(
                "Lưu cột, thứ tự, độ rộng, pin, row groups, values và pivot."
            ).classes("text-xs text-gray-500")
            view_name_input = ui.input(
                label="Tên view",
                placeholder="Ví dụ: FA cơ bản / Pivot theo ngành",
            ).props("outlined autofocus").classes("w-full")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Hủy", on_click=save_view_dialog.close).props(
                    "flat no-caps"
                )
                confirm_save_view_button = ui.button(
                    "Lưu",
                    icon="save",
                ).props("unelevated no-caps")

    # -------------------------------------------------------------------------
    # Grid
    # -------------------------------------------------------------------------
    grid_options: GridOptions = {
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
            "minWidth": 70,
            "floatingFilter": True,
        },
        "columnDefs": _create_grouped_column_defs(
            df=df,
            field_configs=field_configs,
            visible_columns=default_visible_columns,
        ),
        "rowData": dataframe_to_records(df),
        "pagination": True,
        "paginationPageSize": pagination_page_size,
        "animateRows": True,
        "maintainColumnOrder": True,
        "allowDragFromColumnsToolPanel": True,
        "pivotMode": False,
        "rowGroupPanelShow": "onlyWhenGrouping",
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columns",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                    "toolPanelParams": {
                        "suppressColumnMove": False,
                        "suppressRowGroups": False,
                        "suppressValues": False,
                        "suppressPivots": False,
                        "suppressPivotMode": False,
                        "suppressColumnFilter": False,
                        "suppressColumnSelectAll": False,
                        "suppressColumnExpandAll": False,
                        "contractColumnSelection": True,
                    },
                }
            ],
            "defaultToolPanel": "columns",
            "position": "right",
        },
    }

    grid = ui.aggrid(
        grid_options,
        theme="quartz",
        auto_size_columns=False,
        modules="enterprise",
    ).classes(f"w-full h-[{grid_height}]")
    _stop_parent_swipe(grid)

    runtime_state: dict[str, Any] = {
        "session_id": None,
        "ready": False,
        "last_signature": None,
    }

    async def replace_grid_rows(records: list[dict[Hashable, Any]]) -> None:
        """Thay rowData mà không cố ý rebuild column state trên client."""
        try:
            with grid.props.suspend_updates():
                grid.options["rowData"] = records
            await grid.run_grid_method("setGridOption", "rowData", records)
        except Exception:
            grid.options["rowData"] = records
            grid.update()

    def current_filter_values() -> dict[str, list[Any]]:
        values: dict[str, list[Any]] = {}
        for field, selector in selectors.items():
            selected = selector.value or []
            if not isinstance(selected, list):
                selected = [selected]
            values[str(field)] = list(selected)
        return values

    async def apply_filters(_: Any = None) -> None:
        filtered_df = df
        for field, selector in selectors.items():
            selected_values = selector.value or []
            if not isinstance(selected_values, list):
                selected_values = [selected_values]

            normalized_values = [
                str(value)
                for value in selected_values
                if value is not None
            ]
            if normalized_values:
                filtered_df = filtered_df[
                    filtered_df[field]
                    .astype(str)
                    .isin(normalized_values)
                ]

        await replace_grid_rows(dataframe_to_records(filtered_df))

    async def reset_filters(_: Any = None) -> None:
        for selector in selectors.values():
            selector.value = []
            selector.update()

        await replace_grid_rows(dataframe_to_records(df))
        await grid.run_grid_method("setFilterModel", None)
        await persist_state(force=True)

    def refresh_preset_options() -> None:
        saved_filter_select.options = _list_named_presets("filter")
        saved_filter_select.update()
        saved_view_select.options = _list_named_presets("view")
        saved_view_select.update()

    async def persist_state(*, force: bool = False) -> None:
        if not runtime_state["ready"]:
            return

        session_id = runtime_state.get("session_id")
        if not session_id:
            return

        try:
            grid_state = await grid.run_grid_method("getState")
            column_state = await grid.run_grid_method("getColumnState")
        except Exception:
            return

        if not isinstance(grid_state, dict):
            return

        selected_columns = _selected_columns_from_column_state(column_state)
        filter_values = current_filter_values()

        signature = json.dumps(
            {
                "grid_state": grid_state,
                "selected_columns": selected_columns,
                "filter_values": filter_values,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

        if not force and signature == runtime_state.get("last_signature"):
            return

        _save_session_grid_state(
            session_id=str(session_id),
            grid_state=grid_state,
            selected_columns=selected_columns,
            filter_values=filter_values,
        )
        runtime_state["last_signature"] = signature

    # -------------------------------------------------------------------------
    # Saved Filters
    # -------------------------------------------------------------------------
    def open_save_filter_dialog() -> None:
        filter_name_input.value = str(saved_filter_select.value or "")
        filter_name_input.update()
        save_filter_dialog.open()

    async def save_current_filter() -> None:
        name = _normalise_preset_name(filter_name_input.value)
        if not name:
            ui.notify("Nhập tên bộ lọc trước khi lưu", type="warning")
            return

        try:
            filter_model = await grid.run_grid_method("getFilterModel")
        except Exception as exc:
            ui.notify(f"Không đọc được AG Grid filter: {exc}", type="negative")
            return

        preset_name = _save_named_preset(
            "filter",
            name,
            {
                "selector_values": current_filter_values(),
                "filter_model": filter_model if isinstance(filter_model, dict) else {},
            },
        )
        refresh_preset_options()
        saved_filter_select.value = preset_name
        saved_filter_select.update()
        save_filter_dialog.close()
        await persist_state(force=True)
        ui.notify(f"Đã lưu bộ lọc: {preset_name}", type="positive")

    async def load_saved_filter() -> None:
        name = _normalise_preset_name(saved_filter_select.value)
        if not name:
            ui.notify("Chọn một bộ lọc đã lưu", type="warning")
            return

        preset = _load_named_preset("filter", name)
        if preset is None:
            refresh_preset_options()
            ui.notify("Bộ lọc không còn tồn tại", type="warning")
            return

        selector_values = preset.get("selector_values", {})
        if isinstance(selector_values, dict):
            for field, selector in selectors.items():
                values = selector_values.get(str(field), [])
                selector.value = values if isinstance(values, list) else []
                selector.update()

        await apply_filters()

        filter_model = preset.get("filter_model")
        await grid.run_grid_method(
            "setFilterModel",
            filter_model if isinstance(filter_model, dict) and filter_model else None,
        )
        await persist_state(force=True)
        ui.notify(f"Đã tải bộ lọc: {name}", type="positive")

    def delete_saved_filter() -> None:
        name = _normalise_preset_name(saved_filter_select.value)
        if not name:
            ui.notify("Chọn bộ lọc cần xóa", type="warning")
            return

        if _delete_named_preset("filter", name):
            saved_filter_select.value = None
            refresh_preset_options()
            ui.notify(f"Đã xóa bộ lọc: {name}", type="positive")
        else:
            refresh_preset_options()
            ui.notify("Bộ lọc không còn tồn tại", type="warning")

    # -------------------------------------------------------------------------
    # Saved Views
    # -------------------------------------------------------------------------
    def open_save_view_dialog() -> None:
        view_name_input.value = str(saved_view_select.value or "")
        view_name_input.update()
        save_view_dialog.open()

    async def save_current_view() -> None:
        name = _normalise_preset_name(view_name_input.value)
        if not name:
            ui.notify("Nhập tên view trước khi lưu", type="warning")
            return

        try:
            column_state = await grid.run_grid_method("getColumnState")
            column_group_state = await grid.run_grid_method("getColumnGroupState")
            pivot_mode = await grid.run_grid_method("isPivotMode")
        except Exception as exc:
            ui.notify(f"Không đọc được trạng thái view: {exc}", type="negative")
            return

        if not isinstance(column_state, list):
            ui.notify("Column state không hợp lệ", type="negative")
            return

        preset_name = _save_named_preset(
            "view",
            name,
            {
                "column_state": column_state,
                "column_group_state": (
                    column_group_state if isinstance(column_group_state, list) else []
                ),
                "pivot_mode": bool(pivot_mode),
                "selected_columns": _selected_columns_from_column_state(column_state),
            },
        )
        refresh_preset_options()
        saved_view_select.value = preset_name
        saved_view_select.update()
        save_view_dialog.close()
        await persist_state(force=True)
        ui.notify(f"Đã lưu view: {preset_name}", type="positive")

    async def load_saved_view() -> None:
        name = _normalise_preset_name(saved_view_select.value)
        if not name:
            ui.notify("Chọn một view đã lưu", type="warning")
            return

        preset = _load_named_preset("view", name)
        if preset is None:
            refresh_preset_options()
            ui.notify("View không còn tồn tại", type="warning")
            return

        column_state = preset.get("column_state")
        if not isinstance(column_state, list):
            ui.notify("View không có column state hợp lệ", type="negative")
            return

        try:
            await grid.run_grid_method(
                "setPivotMode",
                bool(preset.get("pivot_mode", False)),
            )
            await grid.run_grid_method(
                "applyColumnState",
                {
                    "state": column_state,
                    "applyOrder": True,
                },
            )

            column_group_state = preset.get("column_group_state")
            if isinstance(column_group_state, list):
                await grid.run_grid_method(
                    "setColumnGroupState",
                    column_group_state,
                )

            await grid.run_grid_method("refreshHeader")
        except Exception as exc:
            ui.notify(f"Không tải được view: {exc}", type="negative")
            return

        await persist_state(force=True)
        ui.notify(f"Đã tải view: {name}", type="positive")

    def delete_saved_view() -> None:
        name = _normalise_preset_name(saved_view_select.value)
        if not name:
            ui.notify("Chọn view cần xóa", type="warning")
            return

        if _delete_named_preset("view", name):
            saved_view_select.value = None
            refresh_preset_options()
            ui.notify(f"Đã xóa view: {name}", type="positive")
        else:
            refresh_preset_options()
            ui.notify("View không còn tồn tại", type="warning")

    # -------------------------------------------------------------------------
    # Session restore
    # -------------------------------------------------------------------------
    async def initialise_persisted_state() -> None:
        session_id: str | None = None

        for _ in range(10):
            try:
                session_id = await _get_or_create_grid_session_id()
                if session_id:
                    break
            except Exception:
                await asyncio.sleep(0.15)

        if not session_id:
            return

        runtime_state["session_id"] = session_id
        cached_state = _load_session_grid_state(session_id)

        if cached_state:
            cached_filters = cached_state.get("filter_values", {})
            if isinstance(cached_filters, dict):
                for field, selector in selectors.items():
                    cached_values = cached_filters.get(str(field), [])
                    if isinstance(cached_values, list):
                        selector.value = cached_values
                        selector.update()
                await apply_filters()

            cached_grid_state = cached_state.get("grid_state")
            if isinstance(cached_grid_state, dict):
                for _ in range(10):
                    try:
                        await grid.run_grid_method("setState", cached_grid_state)
                        break
                    except Exception:
                        await asyncio.sleep(0.15)

        runtime_state["ready"] = True
        refresh_preset_options()
        await persist_state(force=True)

    # -------------------------------------------------------------------------
    # Bind events
    # -------------------------------------------------------------------------
    for selector in selectors.values():
        selector.on_value_change(apply_filters)

    reset_button.on_click(reset_filters)

    save_filter_button.on_click(open_save_filter_dialog)
    confirm_save_filter_button.on_click(save_current_filter)
    load_filter_button.on_click(load_saved_filter)
    delete_filter_button.on_click(delete_saved_filter)

    save_view_button.on_click(open_save_view_dialog)
    confirm_save_view_button.on_click(save_current_view)
    load_view_button.on_click(load_saved_view)
    delete_view_button.on_click(delete_saved_view)

    ui.timer(0.1, initialise_persisted_state, once=True)
    ui.timer(1.5, persist_state)

    return grid
