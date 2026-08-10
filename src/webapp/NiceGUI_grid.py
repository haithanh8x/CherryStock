from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd
from nicegui import ui


GridOptions = dict[str, Any]
FieldConfig = Mapping[str, Any]
FilterConfig = Mapping[str, Any]


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
        "headerName": field_name.replace("_", " "),
        "sortable": True,
        "resizable": True,
    }

    if pd.api.types.is_bool_dtype(series):
        column_def.update(
            {
                "filter": "agTextColumnFilter",
                "width": 100,
            }
        )
    elif pd.api.types.is_numeric_dtype(series):
        column_def.update(
            {
                "filter": "agNumberColumnFilter",
                "type": "numericColumn",
                "width": 110,
            }
        )
    elif pd.api.types.is_datetime64_any_dtype(series):
        column_def.update(
            {
                "filter": "agDateColumnFilter",
                "width": 140,
            }
        )
    else:
        column_def.update(
            {
                "filter": "agTextColumnFilter",
                "minWidth": 140,
            }
        )

    return column_def


def create_column_defs(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig] | None = None,
) -> list[GridOptions]:
    """
    Sinh columnDefs động từ DataFrame.

    Khi ``field_configs`` được cung cấp:
    - Thứ tự khai báo config là thứ tự hiển thị cột.
    - ``display=True`` hoặc không khai báo: hiển thị cột.
    - ``display=False``: ẩn hoàn toàn cột khỏi grid.

    Thuộc tính ``display`` là cấu hình phía Python và không được
    truyền sang AG Grid. Nếu ``field_configs`` là None, toàn bộ cột
    của DataFrame sẽ được hiển thị bằng cấu hình mặc định.
    """
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

        aggrid_config = {
            key: value
            for key, value in field_config.items()
            if key != "display"
        }

        column_def.update(aggrid_config)
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


def _create_selectable_column_defs(
    df: pd.DataFrame,
    field_configs: Mapping[str, FieldConfig],
    visible_columns: list[str],
) -> list[GridOptions]:
    """
    Tạo columnDefs cho toàn bộ cột nguồn để có thể bật/tắt động.

    Các field có config được ưu tiên thứ tự trước; các cột còn lại của
    DataFrame được nối phía sau với cấu hình mặc định.
    """
    config_by_column = _field_configs_by_actual_column(df, field_configs)
    visible_set = set(visible_columns)
    ordered_columns: list[Hashable] = []
    seen: set[str] = set()

    for requested_field in field_configs:
        actual_column = _resolve_field_name(df, requested_field)
        if actual_column is None:
            continue

        field_name = str(actual_column)
        if field_name in seen:
            continue

        ordered_columns.append(actual_column)
        seen.add(field_name)

    for column in df.columns:
        field_name = str(column)
        if field_name in seen:
            continue

        ordered_columns.append(column)
        seen.add(field_name)

    column_defs: list[GridOptions] = []

    for column in ordered_columns:
        field_name = str(column)
        field_config = config_by_column.get(field_name, {})
        column_def = _default_column_def(df, column)
        column_def.update(
            {
                key: value
                for key, value in field_config.items()
                if key != "display"
            }
        )
        column_def["hide"] = field_name not in visible_set
        column_defs.append(column_def)

    return column_defs


def _stop_parent_swipe(element: Any) -> None:
    """
    Không cho gesture trong AG Grid nổi lên QTabPanels swipe handler.

    Quasar swipeable xử lý không chỉ touch trên mobile mà còn có thể nhận
    mouse/pointer gesture trên desktop. Vì vậy phải chặn cả ba nhóm event.
    Chỉ stopPropagation, không preventDefault, để scroll/drag trong grid vẫn chạy.
    """
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
    Tạo bộ lọc multiselect, bộ chọn cột hiển thị và AG Grid.

    filter_configs có dạng::

        {
            "Ticker": {"label": "Mã", "width": "w-28"},
            "Stock": {"label": "Sàn", "width": "w-24"},
        }

    field_configs có dạng::

        {
            "Ticker": {
                "display": True,
                "headerName": "Ticker",
                "width": 80,
            },
            "Internal Field": {
                "display": False,
            },
        }

    ``display`` xác định bộ cột được chọn mặc định. Bộ chọn "Cột hiển thị"
    luôn lấy options trực tiếp từ toàn bộ ``df.columns`` nên người dùng có thể
    bật/tắt mọi column có trong nguồn dữ liệu (ví dụ vw_Ticker).

    Thứ tự field_configs được ưu tiên trên grid; các cột chưa cấu hình được
    nối phía sau bằng cấu hình mặc định. Các filter được kết hợp theo AND.
    Mỗi filter cho phép chọn nhiều giá trị theo OR.
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
            valid_filter_fields.append(
                (requested_field, actual_column)
            )

    if missing_fields:
        ui.notify(
            f"Không tìm thấy field: {', '.join(missing_fields)}",
            type="warning",
        )

    selectors: dict[Hashable, ui.select] = {}
    selectable_columns = [str(column) for column in df.columns]
    default_visible_columns = _default_visible_columns(df, field_configs)

    with ui.row().classes(
        "w-full items-end gap-3 mb-4 flex-wrap"
    ):
        for requested_field, actual_column in valid_filter_fields:
            distinct_values = (
                df[actual_column]
                .dropna()
                .astype(str)
                .drop_duplicates()
                .sort_values()
                .tolist()
            )

            filter_config = filter_configs.get(
                requested_field,
                {},
            )
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

        column_selector = (
            ui.select(
                options=selectable_columns,
                value=default_visible_columns,
                label="Cột hiển thị",
                multiple=True,
                with_input=True,
                clearable=True,
            )
            .props(
                "outlined dense options-dense use-chips "
                "popup-content-class=max-h-96"
            )
            .classes("w-96 min-w-72")
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
        "columnDefs": _create_selectable_column_defs(
            df=df,
            field_configs=field_configs,
            visible_columns=default_visible_columns,
        ),
        "rowData": dataframe_to_records(df),
        "pagination": True,
        "paginationPageSize": pagination_page_size,
        "animateRows": True,
    }

    grid = ui.aggrid(
        grid_options,
        theme="quartz",
        auto_size_columns=False,
    ).classes(f"w-full h-[{grid_height}]")
    _stop_parent_swipe(grid)

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

        grid.options["rowData"] = dataframe_to_records(
            filtered_df
        )
        grid.update()

    async def apply_column_visibility(_: Any = None) -> None:
        selected_values = column_selector.value or []

        if not isinstance(selected_values, list):
            selected_values = [selected_values]

        selected_columns = {
            str(value)
            for value in selected_values
            if value is not None and str(value) in selectable_columns
        }

        for column_def in grid.options.get("columnDefs", []):
            field_name = str(column_def.get("field", ""))
            column_def["hide"] = field_name not in selected_columns

        grid.update()

    async def reset_filters(_: Any = None) -> None:
        for selector in selectors.values():
            selector.value = []
            selector.update()

        grid.options["rowData"] = dataframe_to_records(df)
        grid.update()

        await grid.run_grid_method(
            "setFilterModel",
            None,
        )

    for selector in selectors.values():
        selector.on_value_change(apply_filters)

    column_selector.on_value_change(apply_column_visibility)
    reset_button.on_click(reset_filters)

    return grid
