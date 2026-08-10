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
# %%
