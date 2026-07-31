# %%
from DuckDB import Data
from Ults import DuckLib
DuckLib.exportDuckDB_metadata()

# %%
import importlib
from Chart import plot
importlib.reload(plot)
chart = plot.draw_ticker_above_MA('2023-01-01')


# %%
