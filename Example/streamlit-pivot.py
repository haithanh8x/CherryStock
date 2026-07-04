import dash
from dash import dcc, html, Input, Output
import dash_ag_grid as dag
import plotly.express as px
import pandas as pd

app = dash.Dash(__name__)

# --- Dữ liệu mẫu ---
def load_data():
    data = {
        "Khu vực": ["Miền Bắc", "Miền Bắc", "Miền Nam", "Miền Nam", "Miền Trung", "Miền Trung"] * 6,
        "Sản phẩm": ["Điện thoại", "Laptop", "Điện thoại", "Máy tính bảng", "Laptop", "Điện thoại"] * 6,
        "Năm": [2023, 2024, 2023, 2024, 2023, 2024] * 6,
        "Doanh thu ($)": [1500, 2300, 1800, 3100, 1200, 2500] * 6,
        "Số lượng": [10, 12, 15, 18, 8, 14] * 6
    }
    return pd.DataFrame(data)

df = load_data()

# --- Chuẩn bị dữ liệu dạng cây cho AG Grid Tree Data ---
# Mỗi dòng cần cột "path" là 1 list thể hiện đường dẫn cấp bậc: [Khu vực, Sản phẩm, Năm]
df_tree = df.copy()
df_tree["path"] = df_tree.apply(
    lambda r: [r["Khu vực"], r["Sản phẩm"], f"Năm {r['Năm']}"], axis=1
)

column_defs = [
    {"field": "Doanh thu ($)", "aggFunc": "sum", "type": "numericColumn"},
    {"field": "Số lượng", "aggFunc": "sum", "type": "numericColumn"},
]

grid_options = {
    "treeData": True,
    "groupDefaultExpanded": 0,          # thu gọn hết ban đầu, click ▶ để mở từng cấp
    "getDataPath": {"function": "params.data.path"},
    "autoGroupColumnDef": {
        "headerName": "Khu vực / Sản phẩm / Năm",
        "minWidth": 280,
        "cellRendererParams": {"suppressCount": False},  # hiện số lượng dòng con trong ()
    },
    "groupDisplayType": "singleColumn",
    "animateRows": True,
}

# --- Layout chính ---
app.layout = html.Div([
    html.H1("📊 Dashboard Doanh thu"),
    dcc.Tabs(id="tabs", value="tab-doanhthu", children=[
        dcc.Tab(label="💰 Doanh thu theo Khu vực", value="tab-doanhthu"),
        dcc.Tab(label="🌳 Bảng Drill-down (Tree)", value="tab-tree"),
    ]),
    html.Div(id="tab-content")
])

@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):
    if tab == "tab-doanhthu":
        fig = px.bar(df, x="Khu vực", y="Doanh thu ($)", color="Sản phẩm", barmode="group")
        return dcc.Graph(figure=fig)

    elif tab == "tab-tree":
        return html.Div([
            html.P(
                "Click biểu tượng ▶ để mở rộng: Khu vực → Sản phẩm → Năm. "
                "Dòng nhóm tự động cộng dồn (sum) Doanh thu và Số lượng.",
                style={"color": "#555", "marginBottom": "10px"}
            ),
            dag.AgGrid(
                id="tree-grid",
                rowData=df_tree.to_dict("records"),
                columnDefs=column_defs,
                dashGridOptions=grid_options,
                columnSize="sizeToFit",
                style={"height": "600px", "width": "100%"},
                className="ag-theme-alpine",   # theme sáng, gọn — đổi thành "ag-theme-alpine-dark" nếu muốn nền tối
            ),
        ])

if __name__ == "__main__":
    app.run(debug=True)