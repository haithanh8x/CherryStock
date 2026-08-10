"""Source package bootstrap for CherryStock.

Ensures modules under src/ can import the cherrystock package namespace
consistently, regardless of whether entrypoints are executed from project root
or directly from files under src/.
"""

from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parent

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))
