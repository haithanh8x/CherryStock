from typing import Final


filter_configs: Final = {
    "Ticker": {
        "label": "Mã",
        "width": "w-20",
    },
    "Stock": {
        "label": "Sàn",
        "width": "w-20",
    },
    "Industry": {
        "label": "Ngành",
        "width": "w-72",
    },
}


field_configs: Final = {
    "Ticker": {
        "display": True,
        "analysis_group": "GENERAL",
        "headerName": "Ticker",
        "pinned": "left",
        "width": 80,
    },
    "Stock": {
        "display": True,
        "analysis_group": "GENERAL",
        "headerName": "Sàn",
        "width": 70,
    },
    "Company Name": {
        "display": True,
        "analysis_group": "GENERAL",
        "headerName": "Tên công ty",
        "minWidth": 220,
        "flex": 1,
    },
    "Industry": {
        "display": True,
        "analysis_group": "GENERAL",
        "headerName": "Ngành",
        "minWidth": 180,
        "flex": 1,
    },
    "IndustryCode": {
        "display": False,
        "analysis_group": "GENERAL",
        "headerName": "Mã ngành",
        "width": 110,
    },
    "Status": {
        "display": False,
        "analysis_group": "GENERAL",
        "headerName": "Trạng thái",
        "width": 100,
    },
    "Capital": {
        "display": True,
        "analysis_group": "FA",
        "headerName": "Vốn hóa",
        "width": 140,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US')"
        ),
    },
    "Shares Outstanding": {
        "display": False,
        "analysis_group": "FA",
        "headerName": "CP lưu hành",
        "width": 150,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US')"
        ),
    },
    "EPS": {
        "display": True,
        "analysis_group": "FA",
        "headerName": "EPS",
        "width": 100,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US', { "
            "minimumFractionDigits: 2, "
            "maximumFractionDigits: 2 "
            "})"
        ),
    },
    "PE": {
        "display": True,
        "analysis_group": "FA",
        "headerName": "P/E",
        "width": 90,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US', { "
            "minimumFractionDigits: 2, "
            "maximumFractionDigits: 2 "
            "})"
        ),
    },
    "Book Value": {
        "display": True,
        "analysis_group": "FA",
        "headerName": "Giá trị sổ sách",
        "width": 150,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US', { "
            "minimumFractionDigits: 2, "
            "maximumFractionDigits: 2 "
            "})"
        ),
    },
    "ROA": {
        "display": True,
        "analysis_group": "FA",
        "headerName": "ROA",
        "width": 100,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US', { "
            "minimumFractionDigits: 2, "
            "maximumFractionDigits: 2 "
            "}) + '%'"
        ),
    },
    "ROE": {
        "display": True,
        "analysis_group": "FA",
        "headerName": "ROE",
        "width": 100,
        "type": "numericColumn",
        ":valueFormatter": (
            "params => params.value == null "
            "? '' "
            ": params.value.toLocaleString('en-US', { "
            "minimumFractionDigits: 2, "
            "maximumFractionDigits: 2 "
            "}) + '%'"
        ),
    },
}
