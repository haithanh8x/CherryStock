from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Hashable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

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
_GRID_STATE_CACHE_VERSION = 1
_GRID_STATE_CACHE_MAX_SESSIONS = 200
_GRID_STATE_CACHE_LOCK = Lock()
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
    """Dùng Enterprise bundle để có Columns Tool Panel, Row Grouping và Pivot."""
    version = getattr(ui.aggrid, "VERSION", None)
    if not version:
        return

    module_url = os.getenv(
        "AG_GRID_ENTERPRISE_MODULE_URL",
        f"https://cdn.jsdelivr.net/npm/ag-grid-enterprise@{version}/+esm",
    )
    ui.aggrid.set_module_source(module_url)


_configure_aggrid_enterprise()


def dataframe_to_records(
    df: pd.DataFrame,
) -> list[dict[Hashable, Any]]:
    """Chuyển DataFrame thành rowData an toàn cho AG Grid."""
    return (
        df.astype(object)
        .where(df.notna(), None)
        .to_dict("records")
    )


def _resolve_field_name(
    df: pd.DataFrame,
    field_name: str,
) -> Hashable | None:
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


def _default_column_def(
    df: pd.DataFrame,
    column: Hashable,
) -> GridOptions:
    """Sinh cấu hình mặc định theo dtype của cột."""
    series = df[column]
    field_name = str(column)

    column_def: GridOptions = {
        "field": field_name,
        "colId": field_name,
        "headerName": field_name.replace("_", " "),
        "sortable": True,
        "resizable": True,
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
                "minWidth": 140,
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
        column_defs.append(column_def)

    return column_defs


def _field_configs_by_actual_column(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig],
) -> dict[str, FieldConfig]:
    """Map field_configs sang đúng tên cột thực tế của DataFrame."""
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
    """Lấy bộ cột hiển thị mặc định theo display trong field_configs."""
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


def _empty_grid_state_cache() -> dict[str, Any]:
    return {
        "version": _GRID_STATE_CACHE_VERSION,
        "sessions": {},
    }


def _read_grid_state_cache() -> dict[str, Any]:
    with _GRID_STATE_CACHE_LOCK:
        if not _GRID_STATE_CACHE_PATH.exists():
            return _empty_grid_state_cache()

        try:
            data = json.loads(_GRID_STATE_CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _empty_grid_state_cache()

        if not isinstance(data, dict):
            return _empty_grid_state_cache()

        sessions = data.get("sessions")
        if not isinstance(sessions, dict):
            data["sessions"] = {}

        data["version"] = _GRID_STATE_CACHE_VERSION
        return data


def _write_grid_state_cache(cache: dict[str, Any]) -> None:
    with _GRID_STATE_CACHE_LOCK:
        _GRID_STATE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_path = _GRID_STATE_CACHE_PATH.with_suffix(
            _GRID_STATE_CACHE_PATH.suffix + ".tmp"
        )
        temp_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(_GRID_STATE_CACHE_PATH)


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
    cache = _read_grid_state_cache()
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

    _write_grid_state_cache(cache)


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


def create_market_grid(
    df: pd.DataFrame,
    *,
    filter_configs: Mapping[str, FilterConfig] | None = None,
    field_configs: Mapping[str, FieldConfig] | None = None,
    grid_height: str = "1000px",
    pagination_page_size: int = 20,
) -> ui.aggrid:
    """
    Stock Screener với Columns Tool Panel chuẩn của AG Grid Enterprise.

    - Columns được nhóm General / FA / TA / Other.
    - Tick/untick trong Columns panel dùng để show/hide column.
    - Pivot Mode hỗ trợ Row Groups, Values và Column Labels.
    - Grid state + selected columns + filter selectors được cache theo browser-tab
      session vào Build/cache/stock_screener_grid_state.json.
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
    selectable_columns = [str(column) for column in df.columns]
    default_visible_columns = _default_visible_columns(df, field_configs)

    with ui.row().classes("w-full items-end gap-3 mb-4 flex-wrap"):
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

        reset_button = (
            ui.button(
                "Xóa bộ lọc",
                icon="filter_alt_off",
            )
            .props("outline")
        )

    grid_options: GridOptions = {
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
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

        grid.options["rowData"] = dataframe_to_records(filtered_df)
        grid.update()

    async def reset_filters(_: Any = None) -> None:
        for selector in selectors.values():
            selector.value = []
            selector.update()

        grid.options["rowData"] = dataframe_to_records(df)
        grid.update()

        await grid.run_grid_method("setFilterModel", None)

    def current_filter_values() -> dict[str, list[Any]]:
        values: dict[str, list[Any]] = {}
        for field, selector in selectors.items():
            selected = selector.value or []
            if not isinstance(selected, list):
                selected = [selected]
            values[str(field)] = list(selected)
        return values

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
        await persist_state(force=True)

    for selector in selectors.values():
        selector.on_value_change(apply_filters)

    reset_button.on_click(reset_filters)

    ui.timer(0.1, initialise_persisted_state, once=True)
    ui.timer(1.5, persist_state)

    return grid
