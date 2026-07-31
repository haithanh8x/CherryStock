from __future__ import annotations

from lstPara import IFRAME_WIDTH, IFRAME_HEIGHT
import html as html_lib
from pathlib import Path
import sys

from flask import Response

from dash import Dash, html

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from Ults.DuckLib import DuckDBManager
from Chart.plot import draw_comparision_main_sub

start_date = "2025-03-23"
symbol_sources = {
	# main
	"remaining_vnindex": {
		"symbol": "VNINDEX_NOT_VIN",
		"source": "custom",
		"color": "#A0AEC0",
		"label_name": "Remaining VNINDEX",
		"target": "main",
	},
	"vnindex": {
		"symbol": "VNINDEX",
		"source": "index",
		"color": "#03FD10",
		"label_name": "VNINDEX",
		"target": "main",
	},
	"btc": {
		"symbol": "BTC-USD",
		"source": "other",
		"color": "#F7931A",
		"label_name": "BTC-USD",
		"target": "main",
	},
	"spx": {
		"symbol": "^SPX",
		"source": "other",
		"color": "#3182CE",
		"label_name": "SPX",
		"target": "main",
	},
	"ndx": {
		"symbol": "^NDX",
		"source": "other",
		"color": "#00B5D8",
		"label_name": "NDX",
		"target": "main",
	},
	"gcz": {
		"symbol": "^GCZ",
		"source": "other",
		"color": "#ECC94B",
		"label_name": "Gold",
		"target": "main",
	},
	"lcoz": {
		"symbol": "^LCOZ",
		"source": "other",
		"color": "#E53E3E",
		"label_name": "Oil",
		"target": "main",
	},
	# sub
	"dxy": {
		"symbol": "DX-Y.NYB",
		"source": "other",
		"color": "#A0AEC0",
		"label_name": "DX-Y.NYB",
		"target": "sub",
	},
	"VND=X": {
		"symbol": "VND=X",
		"source": "other",
		"color": "#FFAA00",
		"label_name": "USD to VND",
		"target": "sub",
	},
}


app = Dash(__name__)


@app.server.route("/chart")
def chart_page():
	try:
		chart = draw_comparision_main_sub(start_date=start_date, symbol_sources=symbol_sources)
		iframe_html = html_lib.escape(f"{chart._html}</script></body></html>")
		outer_html = f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        html, body {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: #0c0d0f;
        }}
        iframe {{
            display: block;
            width: 100%;
            height: 100%;
            border: 0;
        }}
    </style>
</head>
<body>
    <iframe width="{getattr(chart, 'width', IFRAME_WIDTH)}" height="{getattr(chart, 'height', IFRAME_HEIGHT)}" frameBorder="0" srcdoc="{iframe_html}"></iframe>
</body>
</html>"""
		return Response(outer_html, mimetype="text/html")
	except Exception as exc:
		return Response(
			f"<!doctype html><html><body style='background:#111;color:#eee;font-family:Arial,sans-serif;padding:16px;'>"
			f"<h3>Chart error</h3><pre>{exc}</pre></body></html>",
			mimetype="text/html",
		)
	finally:
		DuckDBManager.close_connection()

app.layout = html.Div(
	[
		html.H3("CherryStock - Main/Sub Comparison"),
		html.Iframe(
			src="/chart",
			style={"width": "100%", "height": "900px", "border": "0", "overflow": "hidden"},
		),
	],
	style={"maxWidth": "1400px", "margin": "0 auto", "padding": "16px"},
)


if __name__ == "__main__":
	app.run(debug=False, use_reloader=False)
