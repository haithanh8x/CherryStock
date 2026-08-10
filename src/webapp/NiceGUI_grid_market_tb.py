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
        "headerName": "Ticker",
        "pinned": "left",
        "width": 50,
    },
    "Stock": {
        "display": True,
        "headerName": "Sàn",
        "width": 50,
    },
    "Company Name": {
        "display": True,
        "headerName": "Tên công ty",
        "minWidth": 220,
        "flex": 1,
    },
    "Industry": {
        "display": True,
        "headerName": "Ngành",
        "minWidth": 180,
        "flex": 1,
    },
    "Status": {
        "display": False,
        "headerName": "Trạng thái",
        "minWidth": 28,
        "flex": 1,
    },    
    "Capital": {
        "display": True,
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