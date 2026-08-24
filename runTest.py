# %%

from src.DuckDB import Data
from src.Ults import DuckLib
DuckLib.exportDuckDB_metadata()
# %%
import importlib
from src.Chart import plot
importlib.reload(plot)
chart = plot.draw_ticker_above_MA('2023-01-01')
# %%
from src.CrawlStock.readAmi import upsert_lstTicker
upsert_lstTicker()

from src.Ults.DuckLib import DuckDBManager; 
from src.Ults.DataValidation import validate_data_quality; 
con=DuckDBManager.get_connection(read_only=True); 
print(validate_data_quality(con, 'raw_stock_eod', key_cols=['Ticker','Date'], required_cols=['Ticker','Date','Open','High','Low','Close','Volume'])); 
DuckDBManager.close_connection(con)