# %%
from Chart.plot import draw_comparision_main_sub
from lstPara import START_DATE
start_date = '2025-03-23'
symbol_sources = {
# main
    'remaining_vnindex': {'symbol': 'VNINDEX_NOT_VIN', 'source': 'custom', 'color': '#A0AEC0', 'label_name': 'Remaining VNINDEX', 'target': 'main', },
    'vnindex': {'symbol': 'VNINDEX', 'source': 'index', 'color': '#03FD10', 'label_name': 'VNINDEX', 'target': 'main', },
    'btc': {'symbol': 'BTC-USD', 'source': 'other', 'color': '#F7931A', 'label_name': 'BTC-USD', 'target': 'main', },
    'spx': {'symbol': '^SPX', 'source': 'other', 'color': '#3182CE', 'label_name': 'SPX', 'target': 'main', },
    'ndx': {'symbol': '^NDX', 'source': 'other', 'color': '#00B5D8', 'label_name': 'NDX', 'target': 'main', },
    'gcz': {'symbol': '^GCZ', 'source': 'other', 'color': '#ECC94B', 'label_name': 'Gold', 'target': 'main', },
    'lcoz': {'symbol': '^LCOZ', 'source': 'other', 'color': '#E53E3E', 'label_name': 'Oil', 'target': 'main', },
    'VIX': {'symbol': '^VIX', 'source': 'other', 'color': '#FFAA00', 'label_name': 'VIX', 'target': 'main', },
# sub main
    'dxy': {'symbol': 'DX-Y.NYB', 'source': 'other', 'color': '#A0AEC0', 'label_name': 'DX-Y.NYB', 'target': 'sub', },
    #'USBY10Y': {'symbol': 'USBY10Y', 'source': 'other', 'color': '#FFAA00', 'label_name': 'US Bond 10Y', 'target': 'sub', },
    'VIX': {'symbol': '^VIX', 'source': 'other', 'color': '#FFAA00', 'label_name': 'VIX', 'target': 'sub', },
    'VND=X': {'symbol': 'VND=X', 'source': 'other', 'color': '#FFAA00', 'label_name': 'USD to VND', 'target': 'sub', },
}
draw_comparision_main_sub(start_date=start_date, symbol_sources=symbol_sources)


# %%

