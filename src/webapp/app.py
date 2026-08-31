import http.server
import socketserver
import sys
import webbrowser
from html import escape
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Chart.plot import build_chart_iframe_html, draw_comparision_main_sub, draw_ticker_above_MA
from Ults.lstPara import CHART_START_DATE, IFRAME_WIDTH, IFRAME_HEIGHT
from Presentation.theme import THEME

ROOT = Path(__file__).resolve().parent
PORT = 8000
HOST = '127.0.0.1'

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)


def build_chart_page() -> str:
    symbol_sources = {
    # main
        'remaining_vnindex': {'symbol': 'VNINDEX_NOT_VIN', 'source': 'custom', 'color': THEME['series_remaining_vnindex'], 'label_name': 'Remaining VNINDEX', 'target': 'main', },
        'vnindex': {'symbol': 'VNINDEX', 'source': 'index', 'color': THEME['series_vnindex'], 'label_name': 'VNINDEX', 'target': 'main', },
        'btc': {'symbol': 'BTC-USD', 'source': 'other', 'color': THEME['series_btc'], 'label_name': 'BTC-USD', 'target': 'main', },
        'spx': {'symbol': '^SPX', 'source': 'other', 'color': THEME['series_spx'], 'label_name': 'SPX', 'target': 'main', },
        'ndx': {'symbol': '^NDX', 'source': 'other', 'color': THEME['series_ndx'], 'label_name': 'NDX', 'target': 'main', },
        'gcz': {'symbol': '^GCZ', 'source': 'other', 'color': THEME['series_gold'], 'label_name': 'Gold', 'target': 'main', },
        'lcoz': {'symbol': '^LCOZ', 'source': 'other', 'color': THEME['series_oil'], 'label_name': 'Oil', 'target': 'main', },    
    # sub main
        'dxy': {'symbol':'DX-Y.NYB','source':'other','color':THEME['series_dxy'],'label_name':'DX-Y.NYB','target':'sub'},
        #'USBY10Y' : {'symbol':'USBY10Y','source':'other','color':THEME['series_usdvnd'],'label_name':'US Bond 10Y','target':'sub'},
        #'VIX' : {'symbol':'^VIX','source':'other','color':THEME['series_usdvnd'],'label_name':'VIX','target':'sub'},
        'VND=X' : {'symbol':'VND=X','source':'other','color':THEME['series_usdvnd'],'label_name':'USD to VND','target':'sub'},
    }

    try:
        chart = draw_ticker_above_MA(CHART_START_DATE)
        iframe_html = build_chart_iframe_html(chart, width=IFRAME_WIDTH, height=IFRAME_HEIGHT)
        chart_2 = draw_comparision_main_sub(start_date=CHART_START_DATE, symbol_sources=symbol_sources)
        iframe_html_2 = build_chart_iframe_html(chart_2, width=IFRAME_WIDTH, height=IFRAME_HEIGHT)

        page = f"""<!DOCTYPE html>
        <html lang=\"en\">
        <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>CherryStock Chart</title>
        <style>body {{ margin: 0; padding: 12px; background: {THEME['background']}; color: {THEME['text']}; font-family: Arial, sans-serif; }} </style>
        </head>
        <body>
        <h2>Liên Thị Trường</h2>
        {iframe_html_2}
        <h2>VNINDEX - Tổng số Ticker so với MA(n)</h2>
        {iframe_html}        
        </body>
        </html>
        """
    except Exception as exc:
        page = f"""<!DOCTYPE html>
        <html lang=\"en\">
        <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>CherryStock Chart</title>
        <style>body {{ margin: 0; padding: 12px; background: #111; color: #fff; font-family: Arial, sans-serif; }} </style>
        </head>
        <body>
        <h2>CherryStock</h2>
        <p style=\"color:{THEME['negative']}\">Chart generation failed: {escape(str(exc))}</p>
        </body>
        </html>
        """

    (ROOT / 'chart.html').write_text(page, encoding='utf-8')
    return page


if __name__ == '__main__':
    build_chart_page()
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        url = f'http://{HOST}:{PORT}/chart.html'
        print(f'Serving chart at {url}')
        webbrowser.open(url)
        httpd.serve_forever()